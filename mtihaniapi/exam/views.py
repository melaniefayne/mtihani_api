from celery import shared_task
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import *
from learner.models import Classroom, Student, Teacher
from exam.models import Exam, ExamQuestion, ExamQuestionAnalysis, StudentExamSession, StudentExamSessionAnswer
from exam.serializers import ExamQuestionSerializer, ExamSerializer, FullStudentExamSessionAnswerSerializer, StudentExamSessionAnswerSerializer, StudentExamSessionSerializer
from gen.curriculum import get_cbc_grouped_questions, get_rubrics_by_sub_strand
from gen.utils import generate_llm_answer_grades_list, generate_llm_question_list, get_db_question_objects
from utils import GlobalPagination, get_answer_expectation_level
from permissions import IsAdmin, IsStudent, IsTeacher, IsTeacherOrStudent
from rest_framework.response import Response
from typing import Counter, Dict, Any, List, Optional, Union
from django.utils.dateparse import parse_datetime
from django.db.models import Q
import json


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def edit_classroom_exam(request) -> Response:
    try:
        exam_id = request.GET.get("exam_id")
        try:
            exam = Exam.objects.get(id=exam_id, teacher__user=request.user)
        except Exam.DoesNotExist:
            return Response({"message": "Exam not found or permission denied."}, status=HTTP_404_NOT_FOUND)

        start_dt_str = request.data.get("start_date_time")
        end_dt_str = request.data.get("end_date_time")
        is_published = request.data.get("is_published")

        if (start_dt_str and not end_dt_str) or (end_dt_str and not start_dt_str):
            return Response({
                "message": "Both start_date_time and end_date_time must be provided together."
            }, status=HTTP_400_BAD_REQUEST)

        if start_dt_str and end_dt_str:
            start_dt = parse_datetime(start_dt_str)
            end_dt = parse_datetime(end_dt_str)
            if not start_dt or not end_dt:
                return Response({
                    "message": "Invalid date format. Use ISO 8601 format (e.g. 2025-05-10T09:00:00Z)."
                }, status=HTTP_400_BAD_REQUEST)

            if timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt)
            if timezone.is_naive(end_dt):
                end_dt = timezone.make_aware(end_dt)

            exam.start_date_time = start_dt
            exam.end_date_time = end_dt

        success_msg = "Exam updated successfully."
        if is_published is not None:
            exam.is_published = bool(is_published)
            success_msg = (
                "Exam published successfully! Your students are now able to view this exam"
                if exam.is_published else
                "Exam unpublished successfully! Publish the exam for your students to access it"
            )

        exam.save()
        serializer = ExamSerializer(exam)

        return Response({
            "message": success_msg,
            "new_exam": serializer.data
        }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Edit exam failed: {e}")
        return Response({
            "message": "Something went wrong while updating the exam."
        }, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def edit_exam_questions(request) -> Response:
    try:
        question_edits = request.data.get("questions", [])
        if not question_edits or not isinstance(question_edits, list):
            return Response({"message": "Please provide a list of questions to edit."}, status=HTTP_400_BAD_REQUEST)

        updated_questions = []

        for q in question_edits:
            required_fields = ["id", "bloom_skill",
                               "description", "expected_answer"]
            if not all(k in q for k in required_fields):
                return Response({
                    "message": f"Each question must include: {', '.join(required_fields)}"
                }, status=HTTP_400_BAD_REQUEST)

            try:
                question = ExamQuestion.objects.select_related(
                    "exam__teacher").get(id=q["id"])
            except ExamQuestion.DoesNotExist:
                return Response({"message": f"Question with ID {q['id']} not found."}, status=HTTP_404_NOT_FOUND)

            if question.exam.teacher.user != request.user:
                return Response({"message": "You do not have permission to edit this question."},
                                status=HTTP_403_FORBIDDEN)

            question.bloom_skill = q["bloom_skill"]
            question.description = q["description"]
            question.expected_answer = q["expected_answer"]
            question.save()

            updated_questions.append(question)

        if updated_questions:
            exam = updated_questions[0].exam
            calculate_exam_analysis(exam)

            serializer = ExamSerializer(exam)
            return Response({
                "message": f"{len(updated_questions)} question(s) updated successfully.",
                "new_exam": serializer.data
            }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Batch edit failed: {e}")
        return Response({"message": "Something went wrong while editing the questions."},
                        status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacherOrStudent])
def get_user_exams(request):
    try:
        user = request.user
        filters = Q()
        exams = Exam.objects.none()
        student_exam_session_map = {}

        # === TEACHER FLOW ===
        if hasattr(user, 'teacher'):
            classrooms = user.teacher.classrooms.all()
            filters &= Q(classroom__in=classrooms)

        # === STUDENT FLOW ===
        elif user.groups.filter(name="student").exists():
            student_records = Student.objects.filter(
                user=user).select_related("classroom")

            if not student_records.exists():
                return Response({"message": "Student record not found."}, status=HTTP_404_NOT_FOUND)

            classrooms = [s.classroom for s in student_records if s.classroom]
            filters &= Q(classroom__in=classrooms) & Q(is_published=True)

        else:
            return Response({"message": "Only teachers or students can access exams."}, status=HTTP_403_FORBIDDEN)

        # === OPTIONAL FILTERS ===
        classroom_id = request.GET.get("classroom_id")
        if classroom_id:
            filters &= Q(classroom__id=classroom_id)

        status = request.GET.get("status")
        if status:
            filters &= Q(status=status)

        is_published = request.GET.get("is_published")
        if is_published is not None:
            filters &= Q(is_published=is_published.lower() == "true")

        # === FETCH EXAMS ===
        exams = Exam.objects.filter(filters).select_related(
            'classroom', 'teacher', 'analysis'
        ).order_by('-start_date_time')

        # === AUTO-UPDATE STALE EXAM STATUS ===
        now = timezone.now()
        possibly_stale_exams = exams.filter(
            Q(status="Upcoming", start_date_time__lte=now, end_date_time__gte=now) |
            Q(status="Ongoing", end_date_time__lt=now)
        )
        print(f"Updating {len(possibly_stale_exams)} exams")
        for exam in possibly_stale_exams:
            exam.refresh_status()

        for exam in exams:
            if (exam.status == "Grading" and not exam.is_grading):
                # Trigger background task
                generate_exam_grades.delay(exam.id)

        # === FETCH STUDENT SESSION MAPPING ===
        if user.groups.filter(name="student").exists():
            student_exam_sessions = StudentExamSession.objects.filter(
                student__in=student_records,
                exam__in=exams
            )
            student_exam_session_map = {
                s.exam_id: s.student_id for s in student_exam_sessions
            }

        elif hasattr(user, 'teacher'):
            student_id = request.GET.get("student_id")
            if student_id:
                try:
                    student = Student.objects.select_related(
                        'classroom').get(id=student_id)

                    # Ensure teacher is authorized to view this student's exams
                    if student.classroom not in classrooms:
                        return Response({"message": "You are not authorized to view this student's exams."}, status=HTTP_403_FORBIDDEN)

                    student_exam_sessions = StudentExamSession.objects.filter(
                        student=student,
                        exam__in=exams
                    )
                    student_exam_session_map = {
                        s.exam_id: s.student_id for s in student_exam_sessions
                    }
                except Student.DoesNotExist:
                    return Response({"message": "Student not found."}, status=HTTP_404_NOT_FOUND)

        # === PAGINATION ===
        paginator = GlobalPagination()
        paginated_exams = paginator.paginate_queryset(exams, request)

        # === SERIALIZATION ===
        serialized = ExamSerializer(
            paginated_exams,
            many=True,
            context={"student_exam_sessions": student_exam_session_map}
        )

        return paginator.get_paginated_response(serialized.data)

    except Exception as e:
        print(f"Error fetching exams: {e}")
        return Response({"message": "Something went wrong while fetching exams."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exam_questions(request) -> Response:
    try:
        exam_id = request.GET.get("exam_id")
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"message": "Exam not found."}, status=404)

        filters = Q(exam=exam)

        grade = request.GET.get("grade")
        bloom_skill = request.GET.get("bloom_skill")
        strand = request.GET.get("strand")
        sub_strand = request.GET.get("sub_strand")
        search = request.GET.get("search")

        if grade:
            filters &= Q(grade=grade)

        if bloom_skill:
            filters &= Q(bloom_skill__icontains=bloom_skill)

        if strand:
            filters &= Q(strand__icontains=strand)

        if sub_strand:
            filters &= Q(sub_strand__icontains=sub_strand)

        if search:
            filters &= Q(description__icontains=search)

        questions = ExamQuestion.objects.filter(filters).order_by("number")

        paginator = GlobalPagination()
        paginated_qs = paginator.paginate_queryset(questions, request)
        serialized = ExamQuestionSerializer(paginated_qs, many=True)

        return paginator.get_paginated_response(serialized.data)

    except Exception as e:
        print(f"Error fetching exam questions: {e}")
        return Response({"message": "Something went wrong while fetching questions."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_single_exam(request) -> Response:
    try:
        exam_id = request.GET.get("exam_id")

        try:
            exam = Exam.objects.select_related(
                'teacher', 'classroom', 'analysis').get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"message": "Exam not found."}, status=HTTP_400_BAD_REQUEST)

        serializer = ExamSerializer(exam)
        return Response({"exam": serializer.data}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error fetching exam detail: {e}")
        return Response({"message": "Something went wrong while fetching the exam."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudent])
def start_exam_session(request):
    try:
        exam_id = request.GET.get("exam_id")
        student_id = request.GET.get("student_id")

        if not exam_id or not student_id:
            return Response({"message": "Missing exam_id or student_id"}, status=HTTP_400_BAD_REQUEST)

        try:
            exam = Exam.objects.get(id=exam_id)
            student = Student.objects.get(id=student_id)
        except (Exam.DoesNotExist, Student.DoesNotExist):
            return Response({"message": "Exam or Student not found."}, status=HTTP_404_NOT_FOUND)

        # Get or create the session
        session, created = StudentExamSession.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={
                "start_date_time": timezone.now(),
                "status": "Ongoing"
            }
        )

        # If existing but start_time is empty, restart it
        if not created:
            session.start_date_time = timezone.now()
            session.status = "Ongoing"
            session.end_date_time = None
            session.avg_score = None
            session.expectation_level = None
            session.save()

        # Always delete any previous answers and create new ones
        StudentExamSessionAnswer.objects.filter(session=session).delete()
        questions = ExamQuestion.objects.filter(exam=exam)
        StudentExamSessionAnswer.objects.bulk_create([
            StudentExamSessionAnswer(session=session, question=q, description="") for q in questions
        ])

        # Return session info
        res = get_exam_session_data(session)
        return Response(res, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error starting exam session: {e}")
        return Response({"message": "Something went wrong while starting the exam session."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacherOrStudent])
def get_exam_session(request):
    try:
        exam_id = request.GET.get("exam_id")
        is_detailed = request.GET.get("is_detailed")
        student_id = request.GET.get("student_id")

        if not exam_id or not student_id:
            return Response({"message": "Missing exam_id or student_id"}, status=HTTP_400_BAD_REQUEST)

        try:
            exam = Exam.objects.get(id=exam_id)
            student = Student.objects.get(id=student_id)
        except (Exam.DoesNotExist, Student.DoesNotExist):
            return Response({"message": "Exam or Student not found."}, status=HTTP_404_NOT_FOUND)

        session = StudentExamSession.objects.get(student=student, exam=exam)

        res = get_exam_session_data(session, is_detailed)
        return Response(res, status=HTTP_200_OK)

    except StudentExamSession.DoesNotExist:
        return Response({"message": "No exam session found."}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error getting exam session: {e}")
        return Response({"message": "Something went wrong while fetching the exam session."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudent])
def update_exam_answer(request):
    try:
        answer_id = request.GET.get("answer_id")
        try:
            answer = StudentExamSessionAnswer.objects.select_related(
                'session').get(id=answer_id)
        except StudentExamSessionAnswer.DoesNotExist:
            return Response({"message": "Answer not found."}, status=HTTP_404_NOT_FOUND)

        if answer.session.status != "Ongoing" or answer.session.exam.status != "Ongoing":
            return Response(
                {"message": "This session is not active. Answers cannot be updated."},
                status=HTTP_400_BAD_REQUEST
            )

        description = request.data.get("description")

        if description is None:
            return Response({"message": "Missing description field."}, status=HTTP_400_BAD_REQUEST)

        answer.description = description.strip()
        answer.save(update_fields=["description", "updated_at"])

        return Response({"message": "Answer updated successfully."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error updating answer: {e}")
        return Response({"message": "Something went wrong while updating the answer."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


def get_exam_session_data(session, is_detailed: bool = False) -> Dict[str, Any]:
    answers = StudentExamSessionAnswer.objects.filter(session=session)
    session_obj = StudentExamSessionSerializer(session).data
    answers_obj = FullStudentExamSessionAnswerSerializer(
        answers, many=True).data if is_detailed else StudentExamSessionAnswerSerializer(
        answers, many=True).data
    return {
        "session": session_obj,
        "answers": answers_obj
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudent])
def end_exam_session(request):
    try:
        exam_id = request.GET.get("exam_id")
        student_id = request.GET.get("student_id")

        if not exam_id or not student_id:
            return Response({"message": "Missing exam_id or student_id"}, status=HTTP_400_BAD_REQUEST)

        try:
            session = StudentExamSession.objects.get(
                exam_id=exam_id, student_id=student_id)
        except (StudentExamSession.DoesNotExist):
            return Response({"message": "Session or Exam not found."}, status=HTTP_404_NOT_FOUND)

        if (session.status == "Ongoing"):
            now = timezone.now()
            session.end_date_time = now
            session.status = "Grading"
            session.save()

        return Response({
            "message": "Session ended successfully.",
            "session": StudentExamSessionSerializer(session).data
        }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error ending exam session: {e}")
        return Response({"message": "Something went wrong while ending the session."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def mock_exam_answers(request):
    try:
        exam_id = request.GET.get("exam_id")
        answers_list = request.data.get("answers_list")

        if not exam_id or not answers_list:
            return Response({"message": "exam_id and answers_list are required."}, status=HTTP_400_BAD_REQUEST)

        try:
            exam = Exam.objects.get(id=exam_id)
        except (Exam.DoesNotExist):
            return Response({"message": "Exam not found."}, status=HTTP_404_NOT_FOUND)

        for student_answers in answers_list:
            student_id = student_answers.get("id")
            answers = student_answers.get("answers", [])

            student = Student.objects.get(id=student_id)
            now = timezone.now()

            session, _ = StudentExamSession.objects.get_or_create(
                exam=exam, student=student,
                defaults={"start_date_time": now, "end_date_time": now,
                          "status": "Grading"}
            )

            # Optionally update session end time if it was previously blank
            if not session.duration_min:
                session.start_date_time = now
                session.end_date_time = now
                session.status = "Grading"
                session.save()

            for ans in answers:
                question_id = ans.get("question_id")
                answer_text = ans.get("answer")

                question = ExamQuestion.objects.get(id=question_id)

                session_answer, _ = StudentExamSessionAnswer.objects.update_or_create(
                    session=session,
                    question=question,
                    defaults={"description": answer_text}
                )

        return Response({
            "message": f"Successfully mocked exam answers for exam id {exam_id}"
        }, status=HTTP_201_CREATED)

    except Exception as e:
        print(f"Error ending exam session: {e}")
        return Response({"message": "Something went wrong while mocking answers."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_student_exam_sessions(request) -> Response:
    try:
        expectation_level = request.GET.get('expectation_level')
        search_query = request.GET.get('search')

        sessions = StudentExamSession.objects.select_related('student', 'exam')

        if expectation_level:
            sessions = sessions.filter(expectation_level=expectation_level)

        if search_query:
            sessions = sessions.filter(student__name__icontains=search_query)

        sessions = sessions.order_by('-start_date_time')

        # Pagination
        paginator = GlobalPagination()
        paginated_qs = paginator.paginate_queryset(sessions, request)
        serialized = StudentExamSessionSerializer(paginated_qs, many=True)

        return paginator.get_paginated_response(serialized.data)

    except Exception as e:
        print(f"Error fetching exam questions: {e}")
        return Response({"message": "Something went wrong while fetching sessions."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_exam_questions_with_answers(request):
    exam_id = request.GET.get("exam_id")

    if not exam_id:
        return Response({"message": "Missing exam_id"}, status=HTTP_400_BAD_REQUEST)

    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return Response({"message": "Exam not found"}, status=HTTP_404_NOT_FOUND)

    questions = ExamQuestion.objects.filter(exam=exam).order_by("number")

    # Prefetch all answers related to questions in this exam
    answers = StudentExamSessionAnswer.objects.filter(question__exam=exam)

    # Group answers by question ID
    answer_map = {}
    for answer in answers:
        qid = answer.question_id
        answer_map.setdefault(qid, []).append({
            "answer_id": answer.id,
            "description": answer.description
        })

    data = []
    for q in questions:
        data.append({
            "question_id": q.id,
            "question_description": q.description,
            "expected_answer": q.expected_answer,
            "sub_strand": q.sub_strand,
            "answers": answer_map.get(q.id, [])
        })

    return Response(data)


# ========================================================================= LLM FUNCTIONS
# =======================================================================================

APP_QUESTION_COUNT = 25
APP_BLOOM_SKILL_COUNT = 3


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def create_classroom_exam(request) -> Response:
    try:
        classroom_id = request.GET.get("classroom_id")
        if not classroom_id:
            return Response({"message": "Missing classroom_id in request."}, status=HTTP_400_BAD_REQUEST)

        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            return Response({"message": "Classroom not found."}, status=HTTP_400_BAD_REQUEST)

        start_date_time_str = request.data.get("start_date_time")
        end_date_time_str = request.data.get("end_date_time")

        if not start_date_time_str or not end_date_time_str:
            return Response({"message": "Missing start or end date time"}, status=HTTP_400_BAD_REQUEST)

        start_date_time = parse_datetime(start_date_time_str)
        end_date_time = parse_datetime(end_date_time_str)

        if not start_date_time or not end_date_time:
            return Response({"message": "Invalid date format. Use ISO 8601 (e.g. '2025-05-10T09:00:00Z')"},
                            status=HTTP_400_BAD_REQUEST)

        strand_ids = request.data.get("strand_ids", [])
        question_count = request.data.get("question_count", APP_QUESTION_COUNT)
        bloom_skill_count = request.data.get(
            "bloom_skill_count", APP_BLOOM_SKILL_COUNT)
        generation_config = {
            "strand_ids": strand_ids,
            "question_count": question_count,
            "bloom_skill_count": bloom_skill_count
        }

        # Create the Exam
        exam = Exam.objects.create(
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            classroom=classroom,
            teacher=Teacher.objects.get(user=request.user),
            generation_config=json.dumps(generation_config)
        )

        # Eagerly create ExamSession entries for each student
        students = Student.objects.filter(classroom=classroom)
        StudentExamSession.objects.bulk_create([
            StudentExamSession(student=s, exam=exam) for s in students
        ])

        # Trigger background task
        generate_exam_content.delay(exam.id, generation_config)

        return Response({
            "message": "Exam generation has been initiated.",
            "exam_id": exam.id,
            "status": "Generating"
        }, status=HTTP_201_CREATED)

    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please try again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================
# ==========ANY CHANGE TO THIS=================
# =======!!!!RESTART CELERY!!!=================
# =============================================
@shared_task
def generate_exam_content(exam_id, generation_config):
    try:
        exam = Exam.objects.get(id=exam_id)

        exam_res = get_llm_generated_exam(
            strand_ids=generation_config['strand_ids'],
            question_count=generation_config['question_count'],
            bloom_skill_count=generation_config['bloom_skill_count']
        )

        if not isinstance(exam_res, list):
            exam.status = "Failed"
            exam.generation_error = exam_res.get("error", "Unknown LLM error")
            exam.save()
            return

        for item in exam_res:
            ExamQuestion.objects.create(
                number=item.get("number"),
                grade=item.get("grade"),
                strand=item.get("strand"),
                sub_strand=item.get("sub_strand"),
                bloom_skill=item.get("bloom_skill"),
                description=item.get("description"),
                expected_answer=item.get("expected_answer"),
                bloom_skill_options=json.dumps(item.get("bloom_skills", [])),
                question_options=json.dumps(item.get("questions", [])),
                answer_options=json.dumps(item.get("expected_answers", [])),
                exam=exam
            )

        calculate_exam_analysis(exam)

        exam.status = "Upcoming"
        exam.save()
    except Exception as e:
        exam.status = "Failed"
        exam.generation_error = f"Unexpected error: {str(e)}"
        exam.save()
        print(f"Background generation failed for Exam ID {exam_id}: {e}")


def get_llm_generated_exam(
        strand_ids: List[int],
        question_count: Optional[int] = None,
        bloom_skill_count: Optional[int] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    if not strand_ids:
        return []

    try:
        kwargs = {"strand_ids": strand_ids}
        if question_count is not None:
            kwargs["question_count"] = question_count
        if bloom_skill_count is not None:
            kwargs["bloom_skill_count"] = bloom_skill_count

        grouped_questions = get_cbc_grouped_questions(**kwargs)

        all_question_list = generate_llm_question_list(
            grouped_question_data=grouped_questions,
        )

        if not isinstance(all_question_list, list):
            return {"error": all_question_list["error"], "raw": all_question_list}

        exam_questions = get_db_question_objects(
            all_question_list=all_question_list,
        )

        return exam_questions

    except Exception as e:
        return {"error": f"LLM generation failed: {str(e)}"}


def calculate_exam_analysis(exam):
    questions = exam.questions.all()

    analysis_data = {
        "question_count": questions.count(),
        "grade_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.grade for q in questions).items()]),
        "bloom_skill_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.bloom_skill for q in questions).items()]),
        "strand_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.strand for q in questions).items()]),
        "sub_strand_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.sub_strand for q in questions).items()]),
    }

    # Update or create the analysis
    ExamQuestionAnalysis.objects.update_or_create(
        exam=exam,
        defaults=analysis_data
    )


# =============================================
# ==========ANY CHANGE TO THIS=================
# =======!!!!RESTART CELERY!!!=================
# =============================================
@shared_task
def generate_exam_grades(exam_id):
    try:
        exam = Exam.objects.get(id=exam_id)
        exam.update_to_grading()

        questions = exam.questions.all()

        grouped_answers_data = []
        for question in questions:
            answers_qs = StudentExamSessionAnswer.objects.filter(
                question=question)
            student_answers = [
                {
                    "answer_id": ans.id,
                    "answer": ans.description
                }
                for ans in answers_qs
            ]

            grouped_answers_data.append({
                "question_id": question.id,
                "question": question.description,
                "expected_answer": question.expected_answer,
                "rubrics": get_rubrics_by_sub_strand(question.sub_strand),
                "student_answers": student_answers
            })

        grades_res = generate_llm_answer_grades_list(
            grouped_answers_data=grouped_answers_data,
        )

        if not isinstance(grades_res, list):
            exam.status = "Failed"
            exam.generation_error = grades_res.get(
                "error", "Unknown LLM error")
            exam.save()
            return

        # update answer scores

        failed_updates = []
        sessions_to_complete = set()
        for item in grades_res:
            answer_id = item.get("answer_id")
            ai_score = float(item.get("score"))

            if answer_id is None or ai_score is None:
                failed_updates.append(
                    {"answer_id": answer_id, "reason": "Missing answer_id or score"})
                continue
            try:
                answer = StudentExamSessionAnswer.objects.get(id=answer_id)
                # If answer is blank, override score to 0
                if not answer.description.strip():
                    ai_score = 0

                answer.ai_score = ai_score
                answer.score = ai_score
                # answer.expectation_level = get_answer_expectation_level(ai_score)
                answer.save(update_fields=["score", "ai_score",
                                           "expectation_level", "updated_at"])
                sessions_to_complete.add(answer.session_id)

            except StudentExamSessionAnswer.DoesNotExist:
                failed_updates.append(
                    {"answer_id": answer_id, "reason": "Answer not found"})

        if failed_updates:
            exam.status = "Failed"
            exam.generation_error = f"Some updates failed: {json.dumps(failed_updates)}"
            exam.save()
            return

        StudentExamSession.objects.filter(
            id__in=sessions_to_complete).update(status="Complete")
        exam.status = "Analysing"
        exam.is_grading = False
        exam.save()

    except Exception as e:
        exam.status = "Failed"
        exam.generation_error = f"Unexpected error: {str(e)}"
        exam.save()
        print(f"Background grading failed for Exam ID {exam_id}: {e}")


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def retry_exam_llm_function(request) -> Response:
    exam_id = request.GET.get("exam_id")
    try:
        exam = Exam.objects.get(id=exam_id, teacher__user=request.user)
    except Exam.DoesNotExist:
        return Response({"message": "Exam not found or you do not have permission to access it."},
                        status=HTTP_404_NOT_FOUND)\

    if exam.status != "Failed":
        return Response({"message": "Only exams with status 'Failed' can be retried."},
                        status=HTTP_400_BAD_REQUEST)

    if exam.is_grading:
        return retry_exam_grading(exam)
    else:
        return retry_exam_generation(exam)


def retry_exam_generation(exam) -> Response:
    try:
        if exam.status == "Generating":
            return Response({"message": "Exam is already being regenerated."}, status=HTTP_400_BAD_REQUEST)

        # Clear previous error and set back to Generating
        exam.status = "Generating"
        exam.generation_error = None
        exam.save()

        try:
            config = json.loads(exam.generation_config or "{}")
        except json.JSONDecodeError:
            return Response({"message": "Saved generation config is invalid JSON."},
                            status=HTTP_400_BAD_REQUEST)

        if not config.get("strand_ids"):
            return Response({"message": "Exam config is incomplete and cannot be retried."},
                            status=HTTP_400_BAD_REQUEST)

        # Re-trigger async generation
        generate_exam_content.delay(exam.id, config)

        return Response({"message": "Exam generation retry initiated.", "exam_id": exam.id, "status": "Generating"},
                        status=HTTP_202_ACCEPTED)

    except Exception as e:
        print(f"Retry failed: {e}")
        return Response({"message": "Something went wrong during retry. Please try again."},
                        status=HTTP_500_INTERNAL_SERVER_ERROR)


def retry_exam_grading(exam) -> Response:
    try:
        if exam.status == "Grading":
            return Response({"message": "Exam is already being graded."}, status=HTTP_400_BAD_REQUEST)

        # Clear previous error and set back to Grading
        exam.status = "Grading"
        exam.generation_error = None
        exam.save()

        # Re-trigger async generation
        generate_exam_grades.delay(exam.id)

        return Response({"message": "Exam grading retry initiated.", "exam_id": exam.id, "status": "Grading"},
                        status=HTTP_202_ACCEPTED)

    except Exception as e:
        print(f"Retry failed: {e}")
        return Response({"message": "Something went wrong during retry. Please try again."},
                        status=HTTP_500_INTERNAL_SERVER_ERROR)
