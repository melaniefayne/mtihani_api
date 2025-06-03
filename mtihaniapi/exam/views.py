from .models import Exam, ExamQuestion
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from rest_framework.status import HTTP_400_BAD_REQUEST
from django.http import HttpResponse
import math
import itertools

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import StandardScaler
from .models import StudentExamSessionPerformance
from scipy.stats import pearsonr
from collections import defaultdict
from celery import shared_task
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import *
from django.db import transaction
from learner.models import Classroom, Student, Teacher
from exam.models import *
from exam.serializers import *
from gen.curriculum import get_cbc_grouped_questions, get_rubrics_by_sub_strand, get_uncovered_strands_up_to_grade
from gen.utils import *
from utils import GlobalPagination
from permissions import IsAdmin, IsStudent, IsTeacher, IsTeacherOrStudent
from rest_framework.response import Response
from typing import Counter, Dict, Any, List, Optional, Union
from django.utils.dateparse import parse_datetime
from django.db.models import Q
import json
from exam.utils import *
from statistics import mode, stdev

APP_QUESTION_COUNT = 25
APP_BLOOM_SKILL_COUNT = 3
BLOOM_SKILLS = [
    "Knowledge", "Comprehension", "Application", "Analysis", "Synthesis", "Evaluation"
]


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
        filters &= Q(type='Standard')
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

            # # TODO
            if (exam.status == "Analysing" and not exam.is_analysing):
                # Trigger background task
                generate_exam_analysis.delay(exam.id)

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
        exam_id = request.GET.get('exam_id')
        if not exam_id:
            return Response(
                {"message": "Missing required parameter: exam_id"},
                status=HTTP_400_BAD_REQUEST
            )

        expectation_level = request.GET.get('expectation_level')
        search_query = request.GET.get('search')

        sessions = StudentExamSession.objects.select_related(
            'student', 'exam').filter(exam_id=exam_id)

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
        print(f"Error fetching student exam sessions: {e}")
        return Response(
            {"message": "Something went wrong while fetching sessions."},
            status=HTTP_500_INTERNAL_SERVER_ERROR
        )


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


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def edit_answer_score(request) -> Response:
    try:
        answer_id = request.GET.get("answer_id")
        try:
            answer = StudentExamSessionAnswer.objects.select_related(
                'session').get(id=answer_id)
        except StudentExamSessionAnswer.DoesNotExist:
            return Response({"message": "Answer not found."}, status=HTTP_404_NOT_FOUND)

        if answer.session.status != "Complete":
            return Response(
                {"message": "This session is not complete yet. Scores cannot be updated."},
                status=HTTP_400_BAD_REQUEST
            )
        tr_score = float(request.data.get("tr_score"))

        if tr_score is None:
            return Response({"message": "Missing teacher score field."}, status=HTTP_400_BAD_REQUEST)

        answer.tr_score = tr_score
        answer.score = tr_score
        answer.save(update_fields=["score", "tr_score",
                    "expectation_level", "updated_at"])

        # TODO: Trigger exam analysis

        return Response({"message": "Answer updated successfully."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error updating answer: {e}")
        return Response({"message": "Something went wrong while updating the answer."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_class_exam_performance(request) -> Response:
    try:
        exam_id = request.GET.get("exam_id")
        if not exam_id:
            return Response({"message": "Missing exam_id parameter."}, status=HTTP_400_BAD_REQUEST)
        try:
            class_performance = ClassExamPerformance.objects.get(
                exam__id=exam_id)
        except ClassExamPerformance.DoesNotExist:
            return Response({"message": "Class Performance not found."}, status=HTTP_404_NOT_FOUND)

        serializer = ClassExamPerformanceSerializer(class_performance)
        return Response(serializer.data, status=HTTP_200_OK)
    except Exception as e:
        print(f"Error getting class performance answer: {e}")
        return Response({"message": "Something went wrong while getting performance"}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_class_exam_clusters(request) -> Response:
    try:
        exam_id = request.GET.get("exam_id")
        if not exam_id:
            return Response({"message": "Missing exam_id parameter."}, status=HTTP_400_BAD_REQUEST)

        clusters = ExamPerformanceCluster.objects.filter(
            exam__id=exam_id).order_by("cluster_label")
        serializer = ExamPerformanceClusterSerializer(clusters, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error getting class performance clusters: {e}")
        return Response({"message": "Something went wrong while getting clusters"}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_cluster_quiz(request) -> Response:
    try:
        cluster_id = request.GET.get("cluster_id")
        if not cluster_id:
            return Response({"message": "Missing cluster_id parameter."}, status=HTTP_400_BAD_REQUEST)

        follow_up_exam = Exam.objects.filter(
            performance_cluster__id=cluster_id, type="FollowUp").first()
        if not follow_up_exam:
            return Response({"message": "No follow-up quiz found for this cluster."}, status=HTTP_400_BAD_REQUEST)

        questions = ExamQuestion.objects.filter(
            exam=follow_up_exam).order_by("number")
        serializer = ExamQuestionSerializer(questions, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error getting class performance answer: {e}")
        return Response({"message": "Something went wrong while getting cluster quiz"}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def download_cluster_quiz_pdf(request):
    cluster_id = request.GET.get("cluster_id")
    if not cluster_id:
        return Response({"message": "Missing cluster_id parameter."}, status=HTTP_400_BAD_REQUEST)

    follow_up_exam = Exam.objects.filter(
        performance_cluster__id=cluster_id, type="FollowUp").first()
    if not follow_up_exam:
        return Response({"message": "No follow-up quiz found for this cluster."}, status=HTTP_400_BAD_REQUEST)

    questions = ExamQuestion.objects.filter(
        exam=follow_up_exam).order_by("number")
    if not questions.exists():
        return Response({"message": "No questions found for this quiz."}, status=HTTP_400_BAD_REQUEST)

    # --- PDF Generation ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Cluster_{cluster_id}_Quiz.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    title = f"Cluster Follow-Up Quiz\n\n"
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, title)

    p.setFont("Helvetica", 12)
    y = height - 80

    for idx, q in enumerate(questions, start=1):
        q_text = f"{idx}. {q.description}"
        # Wrap text if too long
        for line in split_text(q_text, max_chars=100):
            p.drawString(50, y, line)
            y -= 18
            if y < 80:
                p.showPage()
                y = height - 50
        y -= 10  # extra space between questions

    p.save()
    return response


# ================================================================== GENERATION FUNCTIONS
# =======================================================================================
# =======================================================================================


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
    elif exam.is_analysing:
        return retry_exam_analysis(exam)
    else:
        return retry_exam_generation(exam)


# ==================================================================== GENERATING EXAMS

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
        print(f"Background generation failed for Exam ID {exam.id}: {e}")


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

    strand_dist = [
        {"name": k, "count": v}
        for k, v in Counter(q.strand for q in questions).items()
    ]
    tested_strands = [entry["name"] for entry in strand_dist]

    grade_level = exam.classroom.grade
    uncovered_strands = get_uncovered_strands_up_to_grade(
        grade_level, tested_strands)

    analysis_data = {
        "question_count": questions.count(),
        "grade_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.grade for q in questions).items()]),
        "bloom_skill_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.bloom_skill for q in questions).items()]),
        "strand_distribution": json.dumps(strand_dist),
        "untested_strands": json.dumps(uncovered_strands),
        "sub_strand_distribution": json.dumps([{"name": k, "count": v} for k, v in Counter(q.sub_strand for q in questions).items()]),
    }

    ExamQuestionAnalysis.objects.update_or_create(
        exam=exam,
        defaults=analysis_data
    )


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


# ==================================================================== GRADING EXAMS

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

        failed_grading_updates = []
        sessions_to_complete = set()
        for item in grades_res:
            answer_id = item.get("answer_id")
            ai_score = float(item.get("score"))

            if answer_id is None or ai_score is None:
                failed_grading_updates.append(
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
                failed_grading_updates.append(
                    {"answer_id": answer_id, "reason": "Answer not found"})

        if failed_grading_updates:
            exam.status = "Failed"
            exam.generation_error = f"Some updates failed: {json.dumps(failed_grading_updates)}"
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
        print(f"Background grading failed for Exam ID {exam.id}: {e}")


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


# ==================================================================== ANALYSING EXAMS

# =============================================
# ==========ANY CHANGE TO THIS=================
# =======!!!!RESTART CELERY!!!=================
# =============================================
@shared_task
def generate_exam_analysis(exam_id):
    try:
        exam = Exam.objects.get(id=exam_id)
        exam.update_to_analysing()

        # 1. updateCreate StudentExamSessionPerformance
        error_res = generate_all_exam_session_performances(exam)
        if error_res:
            exam.status = "Failed"
            exam.generation_error = error_res.get("error", "An error occurred")
            if "details" in error_res:
                exam.generation_error += f" | Sessions: {json.dumps(error_res['details'])}"
            exam.save()
            return

        performances = StudentExamSessionPerformance.objects.filter(
            session__exam=exam)

        # 2. updateCreate ClassExamPerformance
        error_res = generate_class_exam_performance(exam, performances)
        if error_res:
            exam.status = "Failed"
            exam.generation_error = error_res.get("error", "An error occurred")
            exam.save()
            return

        # 3. update StudentExamSessionPerformance with ClassExamPerformance
        try:
            class_perf = ClassExamPerformance.objects.get(exam=exam)
            for sp in performances:
                diff = round(sp.avg_score - class_perf.avg_score, 2)
                sp.class_avg_difference = diff
                sp.save()
        except Exception as e:
            exam.status = "Failed"
            exam.generation_error = f"Failed updating student-class diffs: {str(e)}"
            exam.save()
            return

        # 4. create performance clusters
        error_res = generate_exam_performance_clusters(exam, performances)
        if error_res:
            exam.status = "Failed"
            exam.generation_error = error_res.get("error", "An error occurred")
            exam.save()
            return

        # 5. create cluster follow up quizzes
        error_res = generate_all_cluster_follow_ups(exam)
        if error_res:
            exam.status = "Failed"
            exam.generation_error = error_res.get("error", "An error occurred")
            if "details" in error_res:
                exam.generation_error += f" | Clusters: {json.dumps(error_res['details'])}"
            exam.save()
            return

        # # updateCreate ExamQuestionPerformance
        # error_res = generate_exam_question_performance(exam)
        # if error_res:
        #     exam.status = "Failed"
        #     exam.generation_error = error_res.get("error", "An error occurred")
        #     exam.save()
        #     return

        exam.status = "Complete"
        exam.is_analysing = False
        exam.save()

    except Exception as e:
        exam.status = "Failed"
        exam.generation_error = f"Unexpected error: {str(e)}"
        exam.save()
        print(f"Background analysis failed for Exam ID {exam.id}: {e}")


# ------------------------------------------------------------------------ Student exam performance

def generate_all_exam_session_performances(exam) -> Union[None, Dict[str, Any]]:
    sessions = StudentExamSession.objects.filter(exam=exam)

    if not sessions.exists():
        return {"error": f"No student sessions found for exam {exam.id}"}

    failed_updates = []
    for session in sessions:
        error_res = generate_student_exam_performance(session)
        if error_res:
            failed_updates.append(error_res)

    if failed_updates:
        return {"error": "Some updates failed", "details": failed_updates}

    return None


def generate_student_exam_performance(session) -> Union[None, Dict[str, Any]]:
    try:
        answers = session.answers.select_related('question').all()
        if not answers.exists():
            # return {"session_id": session.id,  "reason": "Missing answers"}
            return None

        total_score = 0
        total_possible_score = 0

        bloom_scores = defaultdict(list)
        grade_scores = defaultdict(list)
        strand_scores = defaultdict(list)
        strand_sub_strand_scores = defaultdict(lambda: defaultdict(list))
        strand_bloom_scores = defaultdict(lambda: defaultdict(list))

        total_questions = 0
        answered_questions = 0

        for ans in answers:
            total_questions += 1
            if ans.description.strip():
                answered_questions += 1
            if ans.score is None:
                continue

            score = ans.score
            total_score += score
            total_possible_score += 4

            q = ans.question
            bloom_scores[q.bloom_skill].append(score)
            grade_scores[q.grade].append(score)
            strand_scores[q.strand].append(score)
            strand_sub_strand_scores[q.strand][q.sub_strand].append(score)
            strand_bloom_scores[q.strand][q.bloom_skill].append(score)

        if total_possible_score == 0:
            return {"session_id": session.id,  "reason": "Missing total possible score"}

        avg_score = round((total_score / total_possible_score) * 100, 2)

        # Question Performance
        scored_answers = [(ans.question.id, ans.score)
                          for ans in answers if ans.score is not None]
        sorted_answers = sorted(scored_answers, key=lambda x: x[1])
        best_5 = [qid for qid, _ in sorted_answers[-5:]][::-1]
        worst_5 = [qid for qid, _ in sorted_answers[:5]]

        # Completion Rate
        unanswered_questions = total_questions - answered_questions
        completion_rate = round(
            (answered_questions / total_questions) * 100, 2) if total_questions > 0 else 0

        # Format nested strand scores
        formatted_strand_scores = []
        strand_grade_map = {}
        for ans in answers:
            if ans.question.strand not in strand_grade_map:
                strand_grade_map[ans.question.strand] = ans.question.grade

        for idx, (strand, strand_vals) in enumerate(strand_scores.items()):
            sub_strands = strand_sub_strand_scores[strand]
            formatted_subs = format_scores(sub_strands)
            formatted_blooms = format_scores(strand_bloom_scores[strand])
            strand_grade = strand_grade_map.get(strand)
            strand_name_with_grade = f"{strand} (G{strand_grade})" if strand_grade else strand
            formatted_strand_scores.append({
                "name": strand_name_with_grade,
                "grade": strand_grade,
                "percentage": round(sum(strand_vals) / (len(strand_vals) * 4) * 100, 2),
                "sub_strands": sorted(formatted_subs, key=lambda x: x["percentage"], reverse=True),
                "bloom_skills": sorted(formatted_blooms, key=lambda x: x["percentage"], reverse=True)
            })
        # Format other scores
        bloom_skill_scores = format_scores(bloom_scores)
        grade_scores = format_scores(grade_scores)

        # Save or update performance record
        with transaction.atomic():
            StudentExamSessionPerformance.objects.update_or_create(
                session=session,
                defaults={
                    "avg_score": avg_score,
                    "bloom_skill_scores": json.dumps(bloom_skill_scores),
                    "grade_scores": json.dumps(grade_scores),
                    "strand_scores": json.dumps(formatted_strand_scores),
                    "questions_answered": answered_questions,
                    "questions_unanswered": unanswered_questions,
                    "completion_rate": completion_rate,
                    "best_5_question_ids": json.dumps(best_5),
                    "worst_5_question_ids": json.dumps(worst_5)
                }
            )

        return None

    except Exception as e:
        return {"session_id": session.id,  "reason": f"Error {str(e)}"}


# ------------------------------------------------------------------------ Classroom exam performance


def generate_class_exam_performance(exam, performances) -> Union[None, Dict[str, Any]]:
    if not performances.exists():
        return {"error": "No student performances found for this exam."}

    try:
        class_scores = [p.avg_score for p in performances]
        avg_score = round(mean(class_scores), 2)
        std_dev = round(stdev(class_scores), 2) if len(
            class_scores) > 1 else 0.0
        expectation_counts = defaultdict(int)

        for p in performances:
            expectation_counts[p.avg_expectation_level] += 1

        expectation_level_distribution = [
            {"name": level, "count": count} for level, count in expectation_counts.items()
        ]

        # Score distribution in ranges of 10
        distribution_bins = {f"{i}-{i+9}": 0 for i in range(0, 100, 10)}
        distribution_bins["100"] = 0  # exact 100

        for p in performances:
            score = round(p.avg_score)
            if score == 100:
                distribution_bins["100"] += 1
            else:
                bucket = f"{(score // 10) * 10}-{((score // 10) * 10) + 9}"
                distribution_bins[bucket] += 1

        score_distribution = [
            {"name": k, "count": v}
            for k, v in distribution_bins.items()
            if v > 0
        ]

        # Aggregate scores
        bloom_scores = merge_and_average_score_lists(
            p.bloom_skill_scores for p in performances)
        grade_scores = merge_and_average_score_lists(
            p.grade_scores for p in performances)
        strand_student_mastery = generate_strand_student_mastery(performances)

        class_performance_data = {
            "avg_score": avg_score,
            "avg_expectation_level": get_avg_expectation_level(avg_score),
            "expectation_level_distribution": json.dumps(expectation_level_distribution),
            "score_distribution": json.dumps(score_distribution),
            "score_variance": json.dumps({
                "min": round(min(class_scores), 2),
                "max": round(max(class_scores), 2),
                "std_dev": std_dev
            }),
            "bloom_skill_scores": json.dumps(bloom_scores),
        }
        general_insights_res = generate_llm_class_perf_insights(
            class_performance_data)
        if not isinstance(general_insights_res, list):
            return general_insights_res

        strand_analysis_res = generate_strand_analysis(performances)
        if not isinstance(strand_analysis_res, list):
            return strand_analysis_res

        flagged_sub_strands_res = generate_flagged_sub_strands(performances)
        if not isinstance(flagged_sub_strands_res, list):
            return flagged_sub_strands_res

        # Save/update ClassExamPerformance
        with transaction.atomic():
            ClassExamPerformance.objects.update_or_create(
                exam=exam,
                defaults={
                    "student_count": performances.count(),
                    **class_performance_data,
                    "general_insights": json.dumps(general_insights_res),
                    "grade_scores": json.dumps(grade_scores),
                    "strand_analysis": json.dumps(strand_analysis_res),
                    "strand_student_mastery": json.dumps(strand_student_mastery),
                    "flagged_sub_strands": json.dumps(flagged_sub_strands_res)
                }
            )

        return None

    except Exception as e:
        return {"error": f"Error while generating class performance: {str(e)}"}


def generate_strand_analysis(
    performances, percentile=0.10
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    # Aggregators
    strand_scores_map = defaultdict(list)
    strand_student_scores_map = defaultdict(list)  # For top/bottom students
    strand_sub_strand_scores_map = defaultdict(lambda: defaultdict(list))
    strand_bloom_skill_scores_map = defaultdict(lambda: defaultdict(list))
    strand_grades = {}

    # Gather all data
    for perf in performances:
        strand_scores = json.loads(perf.strand_scores or "[]")
        student = perf.session.student
        exam_id = perf.session.exam.id
        student_id = student.id
        avg_score = perf.avg_score
        avg_expectation_level = perf.avg_expectation_level

        for strand in strand_scores:
            strand_name = strand["name"]
            strand_grade = strand["grade"]
            strand_percentage = strand["percentage"]
            strand_scores_map[strand_name].append(strand_percentage)
            strand_grades[strand_name] = strand_grade
            # Collect student scores per strand
            strand_student_scores_map[strand_name].append({
                "student_name": student.name,
                "avg_score": strand_percentage,
                "avg_expectation_level": avg_expectation_level,
                "exam_id": exam_id,
                "student_id": student_id
            })

            # Sub-strand aggregation
            for sub in strand.get("sub_strands", []):
                strand_sub_strand_scores_map[strand_name][sub["name"]].append(
                    sub["percentage"])

            # Bloom skill aggregation
            for skill in strand.get("bloom_skills", []):
                strand_bloom_skill_scores_map[strand_name][skill["name"]].append(
                    skill["percentage"])

    analysis = []

    for strand_name, strand_scores in strand_scores_map.items():
        if not strand_scores:
            continue

        avg_score = round(mean(strand_scores), 2)
        std_dev = round(stdev(strand_scores), 2) if len(
            strand_scores) > 1 else 0.0
        expectation_level = get_avg_expectation_level(avg_score)
        strand_grade = strand_grades.get(strand_name)

        # -- Top & Bottom Percentile Students --
        students = sorted(
            strand_student_scores_map[strand_name], key=lambda x: x["avg_score"], reverse=True)
        n = len(students)
        top_n_count = max(1, math.ceil(n * percentile))
        bottom_n_count = max(1, math.ceil(n * percentile))
        top_students = students[:top_n_count]
        bottom_students = students[-bottom_n_count:] if bottom_n_count > 0 else []

        # Sub-strand distribution
        sub_strand_distribution = []
        for sub_name, values in strand_sub_strand_scores_map[strand_name].items():
            sub_strand_avg = round(mean(values), 2)
            strand_difference = round(sub_strand_avg - avg_score, 2)
            if strand_difference > 0:
                diff_desc = "Above Strand Average"
            elif strand_difference < 0:
                diff_desc = "Below Strand Average"
            else:
                diff_desc = "Equal to Strand Average"

            sub_strand_distribution.append({
                "name": sub_name,
                "percentage": sub_strand_avg,
                "difference": strand_difference,
                "difference_desc": diff_desc
            })
        sub_strand_distribution.sort(
            key=lambda x: x["percentage"], reverse=True)

        # Bloom skill distribution
        bloom_distribution = []
        for skill_name, values in strand_bloom_skill_scores_map[strand_name].items():
            bloom_distribution.append({
                "name": skill_name,
                "percentage": round(mean(values), 2)
            })
        bloom_distribution.sort(key=lambda x: x["percentage"], reverse=True)

        analysis.append({
            "name": strand_name,
            "grade": strand_grade,
            "avg_score": avg_score,
            "avg_expectation_level": expectation_level,
            "bloom_skill_scores": bloom_distribution,
            "score_variance": {
                "min": round(min(strand_scores), 2),
                "max": round(max(strand_scores), 2),
                "std_dev": std_dev
            },
            "sub_strand_scores": sub_strand_distribution,
            "top_students": top_students,
            "bottom_students": bottom_students,
        })

    strand_insights_res = generate_llm_strand_insights(analysis)

    if not isinstance(strand_insights_res, list):
        return {"error": strand_insights_res.get(
                "error", "Unknown LLM error")}

    insights_lookup = {
        insight['strand']: insight
        for insight in strand_insights_res
    }

    for strand in analysis:
        strand_name = strand['name']
        llm_data = insights_lookup.get(strand_name)
        if llm_data:
            strand['insights'] = llm_data.get('insights', [])
            strand['suggestions'] = llm_data.get('suggestions', [])
        else:
            strand['insights'] = []
            strand['suggestions'] = []

    return analysis
# Output
# [
#   {
#     "strand_name": "Mixtures (G7)",
#     "strand_grade": 7,
#     "avg_score": 74.5,
#     "avg_expectation_level": "Meets",
#     "bloom_skill_scores": [...],
#     "score_variance": {...},
#     "sub_strand_scores": [
#       {
#         "name": "Elements and Compounds",
#         "percentage": 81.2,
#         "difference": 6.7,
#         "difference_desc": "Above Strand Average"
#       },
#       ...
#     ],
#     "top_students": [
#       {"student_name": "Akinyi", "avg_score": 98.2, ...}
#     ],
#     "bottom_students": [
#       {"student_name": "Wanjiru", "avg_score": 44.5, ...}
#     ],
#     "insights": [...],
#     "suggestions": [...],
#   }
# ]


def generate_strand_student_mastery(performances, percentile=0.10) -> Dict[str, Any]:
    student_rows = []

    for perf in performances:
        student_name = perf.session.student.name
        strand_scores = json.loads(perf.strand_scores or "[]")
        strand_score_map = {s["name"]: s["percentage"] for s in strand_scores}
        student_rows.append({
            "name": student_name,
            "avg": perf.avg_score,
            "strand_scores": strand_score_map
        })

    sorted_students = sorted(
        student_rows, key=lambda x: x["avg"], reverse=True
    )

    n = len(sorted_students)
    top_n_count = max(1, math.ceil(n * percentile))
    bottom_n_count = max(1, math.ceil(n * percentile))

    top_n = sorted_students[:top_n_count]
    bottom_n = sorted_students[-bottom_n_count:]

    # Optionally, middle students (e.g., middle 10% for context)
    middle_n = []
    if n >= 3 * max(top_n_count, bottom_n_count):  # enough for a middle group
        middle_start = (n - top_n_count - bottom_n_count) // 2
        middle_n_count = max(1, math.ceil(n * percentile))
        middle_n = sorted_students[middle_start:middle_start + middle_n_count]

    selected_students = top_n + middle_n + bottom_n

    # Get all unique strand names and preserve column order
    strand_names = []
    seen_strands = set()
    for student in selected_students:
        for strand in student["strand_scores"].keys():
            if strand not in seen_strands:
                seen_strands.add(strand)
                strand_names.append(strand)

    # Build final matrix
    matrix = []
    for student in selected_students:
        row = {
            "name": student["name"],
            "scores": [
                round(student["strand_scores"].get(strand, 0.0), 2)
                for strand in strand_names
            ]
        }
        matrix.append(row)

    return {
        "strands": strand_names,
        "students": matrix
    }
# Output:
# {
#   "strands": ["Energy", "Forces", "Living Things"],
#   "students": [
#     {"name": "Akinyi", "scores": [88.0, 76.5, 92.1]},
#     {"name": "Mwangi", "scores": [45.3, 55.2, 64.0]},
#     ...
#   ]
# }


def generate_flagged_sub_strands(
        performances
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    from collections import defaultdict

    # Step 1: Prepare data
    student_sub_scores = []
    all_sub_strands = set()

    for perf in performances:
        strand_scores = json.loads(perf.strand_scores or "[]")
        student_map = {}
        for strand in strand_scores:
            for sub in strand.get("sub_strands", []):
                name = sub["name"]
                student_map[name] = sub["percentage"]
                all_sub_strands.add(name)
        student_sub_scores.append(student_map)

    all_sub_strands = sorted(list(all_sub_strands))
    if len(all_sub_strands) < 2:
        return {"sub_strands": []}

    data = np.array([
        [row.get(name, None) for name in all_sub_strands]
        for row in student_sub_scores
    ], dtype=np.float64)

    mask = ~np.isnan(data)

    correlations_map = defaultdict(list)

    for i, j in itertools.combinations(range(len(all_sub_strands)), 2):
        col_i = data[:, i]
        col_j = data[:, j]
        valid = mask[:, i] & mask[:, j]

        if np.sum(valid) < 3:
            continue

        # Skip if one or both columns are constant
        if np.std(col_i[valid]) == 0 or np.std(col_j[valid]) == 0:
            continue

        corr, _ = pearsonr(col_i[valid], col_j[valid])
        corr = round(corr, 2)

        if abs(corr) < 0.3 or corr == 1.0:
            continue

        name_i, name_j = all_sub_strands[i], all_sub_strands[j]

        correlations_map[name_i].append((name_j, corr))
        correlations_map[name_j].append((name_i, corr))

    result = []

    for name, related in correlations_map.items():
        avg_corr = round(np.mean([c for _, c in related]), 2)
        strongest_pair = min(related, key=lambda x: x[1])  # most negative

        result.append({
            "name": name,
            "average_correlation": avg_corr,
            "strongest_negative_pair": strongest_pair[0],
            "correlation": strongest_pair[1],
        })

    sub_strand_correlations = sorted(
        result, key=lambda x: x["average_correlation"])
    corr_insights_res = generate_llm_sub_strand_corr_insights(
        sub_strand_correlations)

    if not isinstance(corr_insights_res, list):
        return {"error": corr_insights_res.get(
                "error", "Unknown LLM error")}

    return corr_insights_res


# Output
# [
    # {
    #     "pair": ["Elements and Compounds", "Acids, Bases and Indicators"],
    #     "correlation": -0.67,
    #     "insight": "Students who perform well in ...",
    #     "suggestion": "Help students connect ...",
    # }
# ]

# ------------------------------------------------------------------------ Exam performance clusters

def extract_performance_feature_matrix(performances):
    # Gather all possible feature names
    all_bloom_skills = set()
    all_grades = set()
    all_strands = set()
    all_sub_strands = set()

    for perf in performances:
        all_bloom_skills.update(entry["name"] for entry in json.loads(
            perf.bloom_skill_scores or "[]"))
        all_grades.update(entry["name"]
                          for entry in json.loads(perf.grade_scores or "[]"))
        all_strands.update(entry["name"]
                           for entry in json.loads(perf.strand_scores or "[]"))
        # CORRECT: Collect all sub-strand names from inside strand_scores
        for strand in json.loads(perf.strand_scores or "[]"):
            all_sub_strands.update(sub["name"]
                                   for sub in strand.get("sub_strands", []))

    # Sorted list for consistent ordering
    bloom_skills = sorted(f"Skill-{s}" for s in all_bloom_skills)
    grades = sorted(f"Grade-{g}" for g in all_grades)
    strands = sorted(f"Strand-{s}" for s in all_strands)
    sub_strands = sorted(f"SubStrand-{s}" for s in all_sub_strands)

    # All best/worst question IDs
    all_best_qids = set()
    all_worst_qids = set()
    for perf in performances:
        all_best_qids.update(json.loads(perf.best_5_question_ids or "[]"))
        all_worst_qids.update(json.loads(perf.worst_5_question_ids or "[]"))
    best_q_cols = sorted(f"BestQ-{qid}" for qid in all_best_qids)
    worst_q_cols = sorted(f"WorstQ-{qid}" for qid in all_worst_qids)

    feature_columns = (
        ["avg_score", "completion_rate", "class_avg_difference"]
        + bloom_skills + grades + strands + sub_strands
        + best_q_cols + worst_q_cols
    )

    feature_matrix = []
    id_list = []

    for perf in performances:
        row = []
        row.append(perf.avg_score)
        row.append(perf.completion_rate)
        row.append(perf.class_avg_difference)

        # Bloom skills
        bloom_map = {f"Skill-{entry['name']}": entry["percentage"]
                     for entry in json.loads(perf.bloom_skill_scores or "[]")}
        for skill in bloom_skills:
            row.append(bloom_map.get(skill, 0.0))

        # Grades
        grade_map = {f"Grade-{entry['name']}": entry["percentage"]
                     for entry in json.loads(perf.grade_scores or "[]")}
        for g in grades:
            row.append(grade_map.get(g, 0.0))

        # Strands
        strand_map = {f"Strand-{entry['name']}": entry["percentage"]
                      for entry in json.loads(perf.strand_scores or "[]")}
        for s in strands:
            row.append(strand_map.get(s, 0.0))

        # Sub-strands (from nested in strand_scores)
        all_sub_strand_scores = {}
        for strand in json.loads(perf.strand_scores or "[]"):
            for sub in strand.get("sub_strands", []):
                all_sub_strand_scores[f"SubStrand-{sub['name']}"] = sub["percentage"]
        for s in sub_strands:
            row.append(all_sub_strand_scores.get(s, 0.0))

        # Binary columns for best/worst questions
        best_ids = set(json.loads(perf.best_5_question_ids or "[]"))
        worst_ids = set(json.loads(perf.worst_5_question_ids or "[]"))
        for q in best_q_cols:
            qid = int(q.replace("BestQ-", ""))
            row.append(1.0 if qid in best_ids else 0.0)
        for q in worst_q_cols:
            qid = int(q.replace("WorstQ-", ""))
            row.append(1.0 if qid in worst_ids else 0.0)

        feature_matrix.append(row)
        id_list.append(perf.id)

    return feature_matrix, feature_columns, id_list


def cluster_exam_performance(performances: List, use_pca: bool = True, pca_components: int = 3, max_k: int = 6):
    # Step 1: Extract features
    feature_matrix, feature_columns, id_list = extract_performance_feature_matrix(
        performances)
    X = np.array(feature_matrix)

    # Step 2: Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Step 3: PCA
    if use_pca and X_scaled.shape[1] > pca_components:
        pca = PCA(n_components=pca_components)
        X_reduced = pca.fit_transform(X_scaled)
    else:
        X_reduced = X_scaled  # Use full features if not enough columns or PCA not requested

    n_samples = X_reduced.shape[0]
    n_unique = np.unique(X_reduced, axis=0).shape[0]
    k_max = max(2, min(max_k, n_samples, n_unique))

    # Elbow method to find optimal k
    n_samples = X_reduced.shape[0]
    n_unique = np.unique(X_reduced, axis=0).shape[0]
    k_max = max(2, min(max_k, n_samples, n_unique))

    optimal_k = find_elbow(X_reduced, min_k=2, max_k=k_max)
    optimal_k = min(optimal_k, n_unique, n_samples)

    # Final KMeans clustering
    final_kmeans = KMeans(n_clusters=optimal_k, random_state=42)
    labels = final_kmeans.fit_predict(X_reduced)

    return labels, optimal_k, feature_columns, id_list


def generate_exam_performance_clusters(exam, performances) -> Union[None, Dict[str, Any]]:
    try:
        # Delete any existing clusters for this exam
        ExamPerformanceCluster.objects.filter(exam=exam).delete()

        labels, optimal_k, _, _ = cluster_exam_performance(
            performances)
        clusters = [[] for _ in range(optimal_k)]
        for perf, label in zip(performances, labels):
            clusters[label].append(perf)

        for cluster_index, group in enumerate(clusters):
            if not group:
                continue

            # Aggregate scores and expectation levels
            all_scores = [perf.avg_score for perf in group]
            all_expectation_levels = [
                perf.avg_expectation_level for perf in group]
            student_ids = [perf.session.id for perf in group]

            # Aggregate Bloom skill distribution
            bloom_skill_map = defaultdict(list)
            for perf in group:
                for entry in json.loads(perf.bloom_skill_scores or "[]"):
                    bloom_skill_map[entry["name"]].append(entry["percentage"])
            bloom_skill_distribution = sorted(
                [
                    {"name": name, "percentage": round(
                        sum(vals) / len(vals), 2)}
                    for name, vals in bloom_skill_map.items()
                ],
                key=lambda item: item["percentage"],
                reverse=True
            )

            # Aggregate strand and sub-strand distribution
            strand_map = defaultdict(list)
            sub_strand_map = defaultdict(lambda: defaultdict(list))
            for perf in group:
                for strand in json.loads(perf.strand_scores or "[]"):
                    strand_map[strand["name"]].append(strand["percentage"])
                    for sub in strand.get("sub_strands", []):
                        sub_strand_map[strand["name"]][sub["name"]].append(
                            sub["percentage"])

            strand_distribution = []
            for strand_name, strand_vals in strand_map.items():
                strand_avg = round(sum(strand_vals) / len(strand_vals), 2)
                sub_strands = sorted(
                    [
                        {"name": sub_name, "percentage": round(
                            sum(vals) / len(vals), 2)}
                        for sub_name, vals in sub_strand_map[strand_name].items()
                    ],
                    key=lambda item: item["percentage"],
                    reverse=True
                )
                strand_distribution.append({
                    "name": strand_name,
                    "percentage": strand_avg,
                    "sub_strands": sub_strands
                })

            # Compute averages
            avg_score = round(sum(all_scores) / len(all_scores),
                              2) if all_scores else 0.0
            # Use mode or most common expectation level
            try:
                avg_expectation_level = mode(all_expectation_levels)
            except:
                avg_expectation_level = Counter(all_expectation_levels).most_common(1)[
                    0][0] if all_expectation_levels else ""

            best_question_counter = Counter()
            worst_question_counter = Counter()
            for perf in group:
                best_question_counter.update(
                    json.loads(perf.best_5_question_ids or "[]"))
                worst_question_counter.update(
                    json.loads(perf.worst_5_question_ids or "[]"))

            # Top N defining questions for this cluster
            top_best_questions = [qid for qid,
                                  _ in best_question_counter.most_common(5)]
            top_worst_questions = [qid for qid,
                                   _ in worst_question_counter.most_common(5)]

            # Score variance
            score_stddev = round(float(np.std(all_scores)),
                                 2) if all_scores else 0.0
            score_range = [round(float(min(all_scores)), 2), round(
                float(max(all_scores)), 2)] if all_scores else [0.0, 0.0]
            score_variance = {
                "min": score_range[0],
                "max": score_range[1],
                "std_dev": score_stddev,
            }

            # Save to DB
            ExamPerformanceCluster.objects.create(
                exam=exam,
                cluster_label=f"Cluster {chr(65 + cluster_index)}",
                student_session_ids=json.dumps(student_ids),
                avg_score=avg_score,
                avg_expectation_level=avg_expectation_level,
                bloom_skill_scores=json.dumps(bloom_skill_distribution),
                strand_scores=json.dumps(strand_distribution),
                cluster_size=len(group),
                top_best_question_ids=json.dumps(top_best_questions),
                top_worst_question_ids=json.dumps(top_worst_questions),
                score_variance=json.dumps(score_variance),
            )

        return None

    except Exception as e:
        return {"error": f"Cluster Generation Failed for examId {exam.id}: {e}"}


def generate_all_cluster_follow_ups(exam) -> Union[None, Dict[str, Any]]:
    clusters = ExamPerformanceCluster.objects.filter(exam=exam)
    questions = ExamQuestion.objects.filter(exam=exam)

    if not clusters.exists() or not questions.exists():
        return {"error": f"No performance clusters found for exam {exam.id}"}

    failed_generations = []
    for cluster in clusters:
        error_res = generate_cluster_follow_up_quizzes(
            exam, cluster, questions)
        if error_res:
            failed_generations.append(error_res)

    if failed_generations:
        return {"error": "Some updates failed", "details": failed_generations}

    return None


def generate_cluster_follow_up_quizzes(exam, cluster, questions) -> Union[None, Dict[str, Any]]:
    try:
        exam_questions = [
            {
                "question": q.description,
                "expected_answer": q.expected_answer,
                "strand": q.strand,
                "sub_strand": q.sub_strand,
                "bloom_skill": q.bloom_skill,
            }
            for q in questions
        ]
        cluster_performance = {
            "cluster_label": cluster.cluster_label,
            "avg_score": cluster.avg_score,
            "cluster_size": cluster.cluster_size,
            "avg_expectation_level": cluster.avg_expectation_level,
            "score_variance": json.loads(cluster.score_variance or '{}'),
            "bloom_skill_scores": json.loads(cluster.bloom_skill_scores or '[]'),
            "strand_scores": json.loads(cluster.strand_scores or '[]'),
            "top_best_question_ids": json.loads(cluster.top_best_question_ids or '[]'),
            "top_worst_question_ids": json.loads(cluster.top_worst_question_ids or '[]'),
        }

        follow_up_quiz_res = generate_llm_follow_up_quiz(
            exam_questions=exam_questions,
            cluster_performance=cluster_performance,
        )
        if not isinstance(follow_up_quiz_res, list):
            return {"error": follow_up_quiz_res.get("error", "Unknown LLM error")}

        # Create the Exam
        follow_up_exam = Exam.objects.create(
            start_date_time=exam.start_date_time,
            end_date_time=exam.end_date_time,
            status="Complete",
            type="FollowUp",
            source_exam=exam,
            classroom=exam.classroom,
            teacher=exam.teacher,
            performance_cluster=cluster,
        )

        # create exam questions
        for idx, item in enumerate(follow_up_quiz_res):
            ExamQuestion.objects.create(
                number=idx+1,
                grade=int(item.get("grade")),
                strand=item.get("strand"),
                sub_strand=item.get("sub_strand"),
                bloom_skill=item.get("bloom_skill"),
                description=item.get("question"),
                expected_answer=item.get("expected_answer"),
                exam=follow_up_exam
            )

        return None

    except Exception as e:
        return {"cluster_id": cluster.id,  "reason": f"Error {str(e)}"}

# ------------------------------------------------------------------------ Question exam performance


def generate_exam_question_performance(exam) -> Union[None, Dict[str, Any]]:
    questions = exam.questions.all()

    if not questions.exists():
        return {"error": "No questions found for this exam."}

    try:
        for question in questions:
            answers = StudentExamSessionAnswer.objects.filter(
                question=question, session__exam=exam)

            if not answers.exists():
                continue  # No answers for this question, skip

            # Compute average score
            scored_answers = [a.score for a in answers if a.score is not None]
            if not scored_answers:
                avg_score = 0.0
            else:
                avg_score = round(sum(scored_answers) / len(scored_answers), 2)

            # Score distribution per expectation level
            level_counts = defaultdict(int)
            level_answers = defaultdict(list)

            for answer in answers:
                level = answer.expectation_level or "Unclassified"
                level_counts[level] += 1
                level_answers[level].append(answer.id)

            # Filter out levels with count == 0
            score_distribution = [
                {"name": k, "count": v}
                for k, v in level_counts.items()
                if v > 0
            ]

            # Save or update ExamQuestionPerformance
            avg_score = round(sum(scored_answers) / len(scored_answers), 2)
            avg_expectation_level = get_answer_expectation_level(avg_score)
            with transaction.atomic():
                ExamQuestionPerformance.objects.update_or_create(
                    question=question,
                    defaults={
                        "avg_score": avg_score,
                        "avg_expectation_level": avg_expectation_level,
                        "score_distribution": json.dumps(score_distribution),
                        "answers_by_level": json.dumps(level_answers),
                    }
                )
        return None

    except Exception as e:
        return {"error": f"Error while generating question performance: {str(e)}"}


def retry_exam_analysis(exam) -> Response:
    try:
        if exam.status == "Analysing":
            return Response({"message": "Exam is already being analysed."}, status=HTTP_400_BAD_REQUEST)

        # Clear previous error and set back to Analysing
        exam.status = "Analysing"
        exam.generation_error = None
        exam.save()

        # Re-trigger async generation
        generate_exam_analysis.delay(exam.id)

        return Response({"message": "Exam analysis retry initiated.", "exam_id": exam.id, "status": "Analysing"},
                        status=HTTP_202_ACCEPTED)

    except Exception as e:
        print(f"Retry failed: {e}")
        return Response({"message": "Something went wrong during retry. Please try again."},
                        status=HTTP_500_INTERNAL_SERVER_ERROR)
