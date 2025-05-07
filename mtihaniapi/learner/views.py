from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any
from django.db.models import Avg
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import *
from learner.serializers import ClassroomDetailSerializer, ClassroomInputSerializer, StudentSerializer
from permissions import IsStudent, IsTeacher, IsTeacherOrStudent
from utils import GlobalPagination, get_expectation_level
from learner.models import (
    LessonTime, Teacher, TermScore, Classroom, Student)
from exam.models import (
    ClassExamPerformance, StudentExamSessionPerformance)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def create_classroom(request) -> Response:
    try:
        teacher = request.user.teacher  # assumes IsTeacher passed
        name = request.data.get("name")
        grade = request.data.get("grade")

        if Classroom.objects.filter(name=name, grade=grade, teacher=teacher).exists():
            return Response({
                "message": f"A classroom named '{name}' for grade {grade} already exists."
            }, status=HTTP_400_BAD_REQUEST)

        serializer = ClassroomInputSerializer(
            data=request.data, context={"request": request})
        if serializer.is_valid():
            classroom = serializer.save()
            classroom_with_details = _get_classroom_with_details([classroom])
            full_classroom = _get_teacher_classrooms(classroom_with_details)[0]
            return Response({
                "message": "Classroom created successfully",
                "new_classroom": ClassroomDetailSerializer(full_classroom).data}, status=HTTP_201_CREATED)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please ty again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


#  ================================================ get-user-classrooms
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacherOrStudent])
def get_user_classrooms(request) -> Response:
    try:
        user = request.user
        classrooms_list = []

        if user.is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:
                return Response({"message": "Teacher account not found."}, status=HTTP_400_BAD_REQUEST)

            classrooms = teacher.classrooms.all().order_by(
                '-grade').prefetch_related('lesson_times')
            classrooms_with_details = _get_classroom_with_details(classrooms)
            classrooms_list = _get_teacher_classrooms(classrooms_with_details)

        else:
            student_records = Student.objects.filter(
                user=user).select_related('classroom')
            classrooms = [s.classroom for s in student_records if s.classroom]
            classrooms = sorted(
                classrooms, key=lambda c: c.grade, reverse=True)
            classrooms_with_details = _get_classroom_with_details(classrooms)
            classrooms_list = _get_student_classrooms(
                classrooms_with_details, student_records)

        serialized = ClassroomDetailSerializer(classrooms_list, many=True)
        return Response(serialized.data, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error: {e}")
        return Response({
            "message": "Something went wrong on our side :( Please try again later."
        }, status=HTTP_500_INTERNAL_SERVER_ERROR)


def _get_classroom_with_details(classrooms: List[Classroom]) -> List[Dict[str, Any]]:
    classrooms_with_details = []
    today = datetime.now().date()

    for classroom in classrooms:
        upcoming_lessons = []
        for i in range(7):
            target_date = today + timedelta(days=i)
            weekday_name = target_date.strftime("%A")

            for lesson in classroom.lesson_times.all():
                if lesson.day == weekday_name:
                    lesson_datetime = datetime.combine(
                        target_date, lesson.time)
                    upcoming_lessons.append(lesson_datetime.isoformat())

        classrooms_with_details.append({
            "id": classroom.id,
            "name": classroom.name,
            "grade": classroom.grade,
            "school_name": classroom.school_name,
            "school_address": classroom.school_address,
            "subject": classroom.subject,
            "lesson_times": upcoming_lessons,
            "teacher_id": classroom.teacher.id if classroom.teacher else None,
        })

    return classrooms_with_details


def _get_teacher_classrooms(classroom_with_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    full_classrooms = []

    for classroom_data in classroom_with_details:
        classroom_id = classroom_data['id']

        # Count students directly
        student_qs = Student.objects.filter(classroom_id=classroom_id)
        classroom_data["student_count"] = student_qs.count()

        # Avg term score from stored field on students
        avg_score = student_qs.aggregate(avg=Avg('avg_score'))['avg'] or 0.0
        classroom_data["avg_term_score"] = avg_score
        classroom_data["avg_term_expectation_level"] = get_expectation_level(
            avg_score)

        # Avg mtihani score from ClassExamPerformance
        result = ClassExamPerformance.objects.filter(
            classroom_id=classroom_id
        ).aggregate(average_score=Avg('avg_score'))

        avg_mtihani_score = result['average_score'] or 0.0
        classroom_data["avg_mtihani_score"] = avg_mtihani_score
        classroom_data["avg_mtihani_expectation_level"] = get_expectation_level(
            avg_mtihani_score)

        full_classrooms.append(classroom_data)

    return full_classrooms


def _get_student_classrooms(classroom_with_details: List[Dict[str, Any]], students: List[Student]) -> List[Dict[str, Any]]:
    full_classrooms = []
    student_map = {s.classroom_id: s for s in students if s.classroom_id}

    for classroom_data in classroom_with_details:
        classroom_id = classroom_data['id']
        student = student_map.get(classroom_id)

        if not student:
            continue  # skip if somehow no match (shouldn't happen)

        classroom_data["student_code"] = student.code
        classroom_data["avg_term_score"] = student.avg_score
        classroom_data["avg_term_expectation_level"] = student.avg_expectation_level

        # Avg mtihani score
        result = StudentExamSessionPerformance.objects.filter(
            session__student=student
        ).aggregate(average_score=Avg('avg_score'))

        avg_mtihani_score = result['average_score'] or 0.0
        classroom_data["avg_mtihani_score"] = avg_mtihani_score
        classroom_data["avg_mtihani_expectation_level"] = get_expectation_level(
            avg_mtihani_score)

        # Term scores list
        classroom_data["term_scores"] = list(
            TermScore.objects.filter(
                student=student,
            ).order_by('grade', 'term')
            .values('id', 'grade', 'term', 'score', 'expectation_level')
        )

        full_classrooms.append(classroom_data)

    return full_classrooms


#  ================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_classroom_term_scores(request) -> Response:
    try:
        classroom_id = request.GET.get("classroom_id")
        if not classroom_id:
            return Response({"message": "Missing classroom_id in request."}, status=HTTP_400_BAD_REQUEST)

        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            return Response({"message": "Classroom not found."}, status=HTTP_400_BAD_REQUEST)

        # Get all students in this classroom
        students = Student.objects.filter(classroom_id=classroom_id)

        # Get all term scores for these students
        term_scores = TermScore.objects.filter(student__in=students)

        # Group and average
        score_map = defaultdict(list)
        expectation_map = defaultdict(list)

        for ts in term_scores:
            key = (ts.grade, ts.term)
            score_map[key].append(ts.score)
            expectation_map[key].append(ts.expectation_level)

        classroom_term_scores = []
        for (grade, term), scores in score_map.items():
            expectation_levels = expectation_map[(grade, term)]
            most_common_expectation = Counter(expectation_levels).most_common(1)[
                0][0] if expectation_levels else ""
            classroom_term_scores.append({
                "grade": grade,
                "term": term,
                "score": round(sum(scores) / len(scores), 2),
                "expectation_level": most_common_expectation
            })

        return Response({"term_scores": classroom_term_scores}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error: {e}")
        return Response({
            "message": "Something went wrong on our side :( Please try again later."
        }, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_students(request):
    try:
        classroom_id = request.GET.get("classroom_id")
        if not classroom_id:
            return Response({"message": "Missing classroom_id in request."}, status=HTTP_400_BAD_REQUEST)

        students = Student.objects.filter(classroom_id=classroom_id)

        # Filtering
        search = request.GET.get("search")
        if search:
            students = students.filter(name__icontains=search)

        status = request.GET.get("status")
        if status:
            students = students.filter(status=status)

        expectation = request.GET.get("expectation_level")
        if expectation:
            students = students.filter(avg_expectation_level=expectation)

        # Paginate
        paginator = GlobalPagination()
        paginated_students = paginator.paginate_queryset(students, request)
        serializer = StudentSerializer(paginated_students, many=True)

        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        print(f"Error: {e}")
        return Response({
            "message": "Something went wrong on our side :( Please try again later."
        }, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def edit_classroom(request) -> Response:
    try:
        classroom_id = request.GET.get("classroom_id")
        teacher = request.user.teacher
        try:
            classroom = Classroom.objects.get(id=classroom_id, teacher=teacher)
        except Classroom.DoesNotExist:
            return Response({"message": "Classroom not found."}, status=HTTP_404_NOT_FOUND)

        serializer = ClassroomInputSerializer(
            classroom, data=request.data, context={"request": request}, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        # Extract validated data
        validated_data = serializer.validated_data
        lesson_times_data = validated_data.pop('lesson_times', [])
        uploaded_students_data = validated_data.pop('uploaded_students', [])

        # Update top-level classroom fields
        for attr, value in validated_data.items():
            setattr(classroom, attr, value)
        classroom.save()

        # Replace lesson times
        classroom.lesson_times.all().delete()
        for lt in lesson_times_data:
            LessonTime.objects.create(classroom=classroom, **lt)

        for student_data in uploaded_students_data:
            name = student_data['name']
            scores = student_data.get('scores', [])

            try:
                student = Student.objects.get(classroom=classroom, name=name)
                # Update or create scores for each grade/term pair
                for score_data in scores:
                    term_score, _ = TermScore.objects.update_or_create(
                        student=student,
                        grade=score_data['grade'],
                        term=score_data['term'],
                        defaults={"score": score_data['score']}
                    )
                # Update average score & expectation
                all_scores = student.term_scores.all()
                avg = round(sum(s.score for s in all_scores) /
                            len(all_scores), 2)
                student.avg_score = avg
                student.avg_expectation_level = get_expectation_level(avg)
                student.save()

            except Student.DoesNotExist:
                # New student
                score_values = [s['score'] for s in scores if 'score' in s]
                avg_score = round(sum(score_values) /
                                  len(score_values), 2) if score_values else 0.0
                avg_expectation = get_expectation_level(avg_score)

                student = Student.objects.create(
                    name=name,
                    classroom=classroom,
                    avg_score=avg_score,
                    avg_expectation_level=avg_expectation,
                )

                for score_data in scores:
                    TermScore.objects.create(
                        student=student,
                        **score_data
                    )

        classroom_with_details = _get_classroom_with_details([classroom])
        full_classroom = _get_teacher_classrooms(classroom_with_details)[0]
        return Response({
            "message": "Classroom updated successfully.",
            "new_classroom": ClassroomDetailSerializer(full_classroom).data
        }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error updating classroom: {e}")
        return Response({"message": "An unexpected error occurred."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def edit_student(request) -> Response:
    try:
        student_id = request.GET.get("student_id")
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"message": "Student not found."}, status=HTTP_404_NOT_FOUND)

        name = request.data.get("name")
        updated_scores = request.data.get("updated_term_scores", [])

        if name:
            student.name = name

        score_values = []

        for score_data in updated_scores:
            score_id = score_data.get("id")
            grade = score_data.get("grade")
            term = score_data.get("term")
            score = score_data.get("score")

            if grade is None or term is None or score is None:
                continue  # or raise error

            if score_id:
                try:
                    term_score = TermScore.objects.get(
                        id=score_id, student=student)
                    term_score.score = score
                    term_score.expectation_level = get_expectation_level(score)
                    term_score.save()
                    score_values.append(score)
                except TermScore.DoesNotExist:
                    continue  # Or optionally log/raise error

            else:  # Create new
                if TermScore.objects.filter(
                    student=student, grade=grade, term=term
                ).exists():
                    continue

                TermScore.objects.create(
                    student=student,
                    grade=grade,
                    term=term,
                    score=score,
                    expectation_level=get_expectation_level(score)
                )
                score_values.append(score)

        if score_values:
            avg_score = round(sum(score_values) / len(score_values), 2)
            student.avg_score = avg_score
            student.avg_expectation_level = get_expectation_level(
                avg_score)

        student.save()

        return Response({"message": "Student updated successfully."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error updating classroom student: {e}")
        return Response({"message": "An unexpected error occurred."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudent])
def join_classroom(request):
    try:
        user = request.user
        student_code = request.data.get("student_code")

        if not student_code:
            return Response({"message": "Missing student_code for classroom registration."}, status=HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(code=student_code)

            if student.user is not None:
                return Response({"message": "This student code has already been registered."}, status=HTTP_400_BAD_REQUEST)

            if student.name.strip().lower() not in user.get_full_name().strip().lower():
                return Response({"message": "Your first name does not match the name on the student code. Please confirm with your teacher."}, status=HTTP_400_BAD_REQUEST)

        except Student.DoesNotExist:
            return Response({"message": "Invalid student code. No matching student found."}, status=HTTP_404_NOT_FOUND)

        student.user = user
        student.status = "Active"
        student.save()

        return Response({"message": "Classroom registration successful"}, status=HTTP_201_CREATED)

    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please try again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_single_student(request) -> Response:
    try:
        student_id = request.GET.get("student_id")

        if not student_id:
            return Response({"message": "Missing student_id parameter."}, status=HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.select_related(
                "classroom", "user").prefetch_related("term_scores").get(id=student_id)
        except Student.DoesNotExist:
            return Response({"message": "Student not found."}, status=HTTP_404_NOT_FOUND)

        serializer = StudentSerializer(student)
        return Response({"student": serializer.data}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error fetching student detail: {e}")
        return Response({"message": "Something went wrong while fetching the student."}, status=HTTP_500_INTERNAL_SERVER_ERROR)
