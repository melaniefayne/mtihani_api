from datetime import datetime, timedelta
from typing import List, Dict, Any
from django.db.models import Avg
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import *
from learner.serializers import ClassroomDetailSerializer, ClassroomSerializer
from permissions import IsTeacher, IsTeacherOrStudent
from utils import get_expectation_level
from learner.models import (
    Teacher, TermScore, Classroom, ClassroomStudent)
from exam.models import (
    ClassExamPerformance, StudentExamSessionPerformance)


#  ================================================ create-classroom

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

        serializer = ClassroomSerializer(
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

            classrooms = teacher.classrooms.all().order_by('-updated_at').prefetch_related('lesson_times')
            classrooms_with_details = _get_classroom_with_details(classrooms)
            classrooms_list = _get_teacher_classrooms(classrooms_with_details)

        else:
            try:
                student = ClassroomStudent.objects.get(user=user)
            except ClassroomStudent.DoesNotExist:
                return Response({"message": "Student account not found."}, status=HTTP_400_BAD_REQUEST)

            classrooms = student.classroom.all().order_by('-updated_at').prefetch_related('lesson_times')
            classrooms_with_details = _get_classroom_with_details(classrooms)
            classrooms_list = _get_student_classrooms(classrooms_with_details, student)

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

    for classroom in classroom_with_details:
        classroom_id = classroom['id']
        classroom_data = classroom

        student_count = ClassroomStudent.objects.filter(
            classroom__id=classroom_id
        ).count()
        classroom_data["student_count"] = student_count

        result = TermScore.objects.filter(
            classroom_student__classroom__id=classroom_id
        ).aggregate(average_score=Avg('score'))

        avg_term_score = result['average_score'] or 0.0
        classroom_data["avg_term_score"] = avg_term_score
        classroom_data["avg_term_expectation_level"] = get_expectation_level(
            avg_term_score)

        result = ClassExamPerformance.objects.filter(
            classroom_id=classroom_id
        ).aggregate(average_score=Avg('avg_score'))

        avg_mtihani_score = result['average_score'] or 0.0
        classroom_data["avg_mtihani_score"] = avg_mtihani_score
        classroom_data["avg_mtihani_expectation_level"] = get_expectation_level(
            avg_mtihani_score)

        full_classrooms.append(classroom_data)

    return full_classrooms


def _get_student_classrooms(classroom_with_details: List[Dict[str, Any]], student: ClassroomStudent) -> List[Dict[str, Any]]:
    full_classrooms = []

    for classroom in classroom_with_details:
        classroom_id = classroom['id']
        classroom_data = classroom
        classroom_data["student_code"] = student.code

        # Avg term score
        result = TermScore.objects.filter(
            classroom_student=student,
            classroom_student__classrooms__id=classroom_id
        ).aggregate(average_score=Avg('score'))

        avg_term_score = result['average_score'] or 0.0
        classroom_data["avg_term_score"] = avg_term_score
        classroom_data["avg_term_expectation_level"] = get_expectation_level(
            avg_term_score)

        # Avg mtihani score
        result = StudentExamSessionPerformance.objects.filter(
            session__student=student,
            session__exam__classroom_id=classroom_id
        ).aggregate(average_score=Avg('avg_score'))

        avg_mtihani_score = result['average_score'] or 0.0
        classroom_data["avg_mtihani_score"] = avg_mtihani_score
        classroom_data["avg_mtihani_expectation_level"] = get_expectation_level(
            avg_mtihani_score)

        # Term scores list
        term_scores_qs = TermScore.objects.filter(
            classroom_student=student,
            classroom_student__classrooms__id=classroom_id
        ).order_by('grade', 'term')

        classroom_data["term_scores"] = [
            {
                "id": ts.id,
                "grade": ts.grade,
                "term": ts.term,
                "score": ts.score,
                "expectation_level": ts.expectation_level,
            }
            for ts in term_scores_qs
        ]

        full_classrooms.append(classroom_data)

    return full_classrooms


# # ======================== CLASS VIEWS ========================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def create_class(request):
#     try:
#         teacher = Teacher.objects.get(user=request.user)
#     except Teacher.DoesNotExist:
#         return Response({
#             "status": False,
#             "message": "You must create a teacher profile first."}, status=HTTP_400_BAD_REQUEST)

#     data = request.data.copy()
#     data['teacher'] = teacher.id

#     serializer = ClassSerializer(data=data)
#     if serializer.is_valid():
#         class_instance = serializer.save()

#         # Handle optional lesson_times
#         lesson_times = request.data.get('lesson_times', [])
#         for entry in lesson_times:
#             day = entry.get("day")
#             time = entry.get("time")
#             if day and time:
#                 LessonTime.objects.create(
#                     class_ref=class_instance, day=day, time=time)

#         return Response(ClassSerializer(class_instance).data, status=HTTP_201_CREATED)

#     return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


# @api_view(['PATCH'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def update_class(request):
#     class_id = request.data.get("class_id")
#     if not class_id:
#         return Response({"error": "Missing class_id in request."}, status=HTTP_400_BAD_REQUEST)

#     try:
#         teacher = Teacher.objects.get(user=request.user)
#         classroom = Class.objects.get(id=class_id, teacher=teacher)
#     except (Teacher.DoesNotExist, Class.DoesNotExist):
#         return Response({"error": "Class not found or not yours."}, status=404)

#     fields = ["name", "school_name", "school_address", "grade"]
#     updated_fields = []

#     for field in fields:
#         if field in request.data:
#             setattr(classroom, field, request.data[field])
#             updated_fields.append(field)

#     # Save basic class updates first
#     classroom.save()

#     # Handle lesson time updates
#     lesson_times = request.data.get("lesson_times")
#     if lesson_times is not None:
#         if not isinstance(lesson_times, list):
#             return Response({"error": "lesson_times must be a list of {day, time} objects."}, status=HTTP_400_BAD_REQUEST)

#         # Delete old ones
#         classroom.lesson_times.all().delete()

#         # Create new lesson times
#         for entry in lesson_times:
#             day = entry.get("day")
#             time = entry.get("time")
#             if day and time:
#                 LessonTime.objects.create(
#                     class_ref=classroom, day=day, time=time)

#         updated_fields.append("lesson_times")

#     return Response({
#         "status": "Class updated",
#         "updated_fields": updated_fields,
#         "class_id": classroom.id
#     }, status=HTTP_200_OK)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def class_detail(request, class_id):
#     try:
#         teacher = Teacher.objects.get(user=request.user)
#         classroom = Class.objects.get(id=class_id, teacher=teacher)
#     except (Teacher.DoesNotExist, Class.DoesNotExist):
#         return Response({"error": "Class not found or not yours."}, status=404)

#     # Overall class average
#     overall_avg = (
#         TermScore.objects
#         .filter(student__classroom=classroom)
#         .aggregate(avg=Avg("score"))["avg"]
#     )

#     # Average per term
#     term_averages = (
#         TermScore.objects
#         .filter(student__classroom=classroom)
#         .values("grade", "term")
#         .annotate(avg_score=Avg("score"))
#         .order_by("grade", "term")
#     )

#     return Response({
#         "id": classroom.id,
#         "name": classroom.name,
#         "grade": classroom.grade,
#         "school_name": classroom.school_name,
#         "school_address": classroom.school_address,
#         "code": classroom.code,
#         "class_average": round(overall_avg, 2),
#         "class_expectation": get_expectation_level(overall_avg),
#         "term_score_averages": [
#             {
#                 "grade": a["grade"],
#                 "term": a["term"],
#                 "average_score": round(a["avg_score"], 2) if a["avg_score"] else None,

#             } for a in term_averages
#         ]
#     }, status=HTTP_200_OK)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def students_in_class(request, class_id):
#     try:
#         teacher = Teacher.objects.get(user=request.user)
#         classroom = Class.objects.get(id=class_id, teacher=teacher)
#     except (Teacher.DoesNotExist, Class.DoesNotExist):
#         return Response({"error": "Class not found or not yours."}, status=404)

#     students = classroom.students.prefetch_related("term_scores").all()

#     # 🔍 Search filter
#     search_query = request.GET.get("search")
#     if search_query:
#         students = students.filter(
#             Q(name__icontains=search_query) | Q(code__icontains=search_query)
#         )

#     # 🧠 Add student average as annotation (so we can order)
#     students = students.annotate(avg_score=Avg("term_scores__score"))

#     # ⬆️⬇️ Ordering
#     ordering = request.GET.get("ordering")
#     if ordering:
#         if ordering.lstrip("-") in ["name", "avg_score"]:
#             students = students.order_by(ordering)

#     # 📄 Pagination
#     paginator = GlobalPagination()
#     page = paginator.paginate_queryset(students, request)

#     student_data = []
#     for student in page:
#         scores = student.term_scores.all().values(
#             "grade", "term", "score").order_by("grade", "term")
#         term_scores = [
#             {
#                 "grade": s["grade"],
#                 "term": s["term"],
#                 "score": s["score"],
#                 "expectation": get_expectation_level(s["score"])
#             }
#             for s in scores
#         ]
#         student_data.append({
#             "id": student.id,
#             "name": student.name,
#             "code": student.code,
#             "term_scores": term_scores,
#             "average_score": round(student.avg_score, 2) if student.avg_score else None,
#             "average_expectation": get_expectation_level(student.avg_score) if student.avg_score else None
#         })

#     return paginator.get_paginated_response(student_data)


# # ======================== TEACHER VIEWS ========================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def create_teacher(request):
#     if Teacher.objects.filter(user=request.user).exists():
#         return Response({"error": "Teacher profile already exists."}, status=HTTP_400_BAD_REQUEST)

#     phone_no = request.data.get("phone_no")
#     if not phone_no:
#         return Response({"error": "Phone number is required."}, status=HTTP_400_BAD_REQUEST)

#     teacher = Teacher.objects.create(
#         user=request.user,
#         phone_no=phone_no
#     )

#     return Response({
#         "status": "Teacher profile created",
#         "teacher_id": teacher.id
#     }, status=HTTP_201_CREATED)


# @api_view(['PATCH'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def update_teacher(request):
#     try:
#         teacher = Teacher.objects.get(user=request.user)
#     except Teacher.DoesNotExist:
#         return Response({"error": "Teacher profile not found."}, status=404)

#     phone = request.data.get("phone_no")
#     if phone:
#         teacher.phone_no = phone
#         teacher.save()
#         return Response({"status": "Phone updated"})
#     return Response({"error": "No phone number provided."}, status=HTTP_400_BAD_REQUEST)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def my_classes(request):
#     try:
#         teacher = Teacher.objects.get(user=request.user)
#     except Teacher.DoesNotExist:
#         return Response({"error": "Teacher profile not found."}, status=404)

#     classes = teacher.classes.all()

#     data = []
#     for c in classes:
#         lesson_times = c.lesson_times.all().values("day", "time")
#         data.append({
#             "id": c.id,
#             "name": c.name,
#             "grade": c.grade,
#             "school_name": c.school_name,
#             "school_address": c.school_address,
#             "code": c.code,
#             "lesson_times": list(lesson_times)
#         })

#     return Response(data, status=HTTP_200_OK)


# # ======================== STUDENT VIEWS ========================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated, IsTeacher])
# @parser_classes([MultiPartParser])
# def upload_students_csv(request):
#     csv_file = request.FILES.get('file')
#     class_id = request.POST.get("class_id")

#     if not csv_file:
#         return Response({"error": "No file uploaded."}, status=HTTP_400_BAD_REQUEST)

#     if not csv_file.name.endswith('.csv'):
#         return Response({"error": "Only CSV files are supported."}, status=HTTP_400_BAD_REQUEST)

#     if not class_id:
#         return Response({"error": "Missing class_id in request."}, status=HTTP_400_BAD_REQUEST)

#     # Get teacher and class
#     try:
#         teacher = Teacher.objects.get(user=request.user)
#         classroom = Class.objects.get(id=class_id, teacher=teacher)
#     except Teacher.DoesNotExist:
#         return Response({"error": "Teacher profile not found."}, status=HTTP_400_BAD_REQUEST)
#     except Class.DoesNotExist:
#         return Response({"error": "Class not found or not assigned to you."}, status=404)

#     try:
#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         reader = csv.DictReader(io_string)
#     except Exception as e:
#         return Response({"error": f"Failed to parse CSV: {str(e)}"}, status=HTTP_400_BAD_REQUEST)

#     created_students = []

#     for row in reader:
#         name = row.get('student_name')
#         if not name:
#             continue

#         student, _ = Student.objects.get_or_create(
#             name=name,
#             classroom=classroom,
#             defaults={"code": generate_unique_code()}
#         )
#         created_students.append(student.name)

#         for col, value in row.items():
#             if not col:
#                 continue

#             match = re.match(r"Grade(\d+)Term(\d+)Score", col)
#             if match and value and value.strip():
#                 try:
#                     grade = int(match.group(1))
#                     term = int(match.group(2))
#                     score = float(value.strip())
#                     TermScore.objects.update_or_create(
#                         student=student,
#                         grade=grade,
#                         term=term,
#                         defaults={"score": score}
#                     )
#                 except (ValueError, TypeError):
#                     continue

#     return Response({
#         "status": "success",
#         "created_students": created_students,
#         "class": classroom.name,
#         "grade": classroom.grade
#     }, status=HTTP_201_CREATED)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated, IsTeacher])
# def upsert_term_scores(request):
#     student_id = request.data.get("student_id")
#     scores = request.data.get("scores", [])

#     if not student_id or not isinstance(scores, list):
#         return Response({"error": "Missing student_id or invalid scores list."}, status=HTTP_400_BAD_REQUEST)

#     try:
#         student = Student.objects.get(
#             id=student_id, classroom__teacher__user=request.user)
#     except Student.DoesNotExist:
#         return Response({"error": "Student not found or not in your class."}, status=404)

#     result = []

#     for entry in scores:
#         grade = entry.get("grade")
#         term = entry.get("term")
#         score = entry.get("score")

#         if not all([grade, term, score]):
#             result.append({
#                 "grade": grade,
#                 "term": term,
#                 "status": "skipped",
#                 "reason": "Missing grade, term, or score"
#             })
#             continue

#         term_score, created = TermScore.objects.update_or_create(
#             student=student,
#             grade=grade,
#             term=term,
#             defaults={"score": score}
#         )

#         result.append({
#             "grade": grade,
#             "term": term,
#             "score": term_score.score,
#             "status": "created" if created else "updated"
#         })

#     return Response({
#         "student": student.name,
#         "student_id": student.id,
#         "results": result
#     }, status=HTTP_200_OK)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def my_term_scores(request):
#     try:
#         student = Student.objects.get(user=request.user)
#     except Student.DoesNotExist:
#         return Response({"error": "Student profile not found."}, status=404)

#     scores = student.term_scores.all().order_by("grade", "term")
#     score_list = []

#     for score in scores:
#         score_list.append({
#             "grade": score.grade,
#             "term": score.term,
#             "score": score.score,
#             "expectation": get_expectation_level(score.score)
#         })

#     # Average
#     avg = scores.aggregate(avg=Avg("score"))["avg"]

#     return Response({
#         "student_id": student.id,
#         "name": student.name,
#         "code": student.code,
#         "term_scores": score_list,
#         "average_score": round(avg, 2) if avg else None,
#         "average_expectation": get_expectation_level(avg) if avg else None
#     }, status=HTTP_200_OK)
