import json
from celery import shared_task
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import *
from gen.curriculum import get_cbc_grouped_questions, get_rubrics_by_sub_strand
from gen.utils import generate_llm_answer_grades_list, generate_llm_question_list, get_db_question_objects
from learner.models import Classroom, Student, Teacher
from exam.models import Exam, ExamQuestion, ExamQuestionAnalysis, StudentExamSession, StudentExamSessionAnswer
from permissions import  IsTeacher
from rest_framework.response import Response
from typing import List, Dict, Optional, Union, Any
from collections import Counter
from django.utils.dateparse import parse_datetime
from django.db.models import Q


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
        for item in grades_res:
            answer_id = item.get("answer_id")
            score = item.get("score")

            if answer_id is None or score is None:
                failed_updates.append(
                    {"answer_id": answer_id, "reason": "Missing answer_id or score"})
                continue
            try:
                answer = StudentExamSessionAnswer.objects.get(id=answer_id)
                answer.score = score
                answer.save()
            except StudentExamSessionAnswer.DoesNotExist:
                failed_updates.append(
                    {"answer_id": answer_id, "reason": "Answer not found"})

        if failed_updates:
            exam.status = "Failed"
            exam.generation_error = f"Some updates failed: {json.dumps(failed_updates)}"
            exam.save()
            return

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
