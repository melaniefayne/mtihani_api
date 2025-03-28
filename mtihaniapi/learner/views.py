# learner/views.py
import csv
import io
import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from .models import Teacher, LessonTime
from .serializers import ClassSerializer
from learner.models import Student, TermScore, Teacher, Class
from permissions import IsTeacher
from utils import generate_unique_code, GlobalPagination, get_expectation_level
from django.db.models import Avg, Q


# ======================== CLASS VIEWS ========================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def create_class(request):
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return Response({"error": "You must create a teacher profile first."}, status=400)

    data = request.data.copy()
    data['teacher'] = teacher.id

    serializer = ClassSerializer(data=data)
    if serializer.is_valid():
        class_instance = serializer.save()

        # Handle optional lesson_times
        lesson_times = request.data.get('lesson_times', [])
        for entry in lesson_times:
            day = entry.get("day")
            time = entry.get("time")
            if day and time:
                LessonTime.objects.create(class_ref=class_instance, day=day, time=time)

        return Response(ClassSerializer(class_instance).data, status=201)
    
    return Response(serializer.errors, status=400)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsTeacher])
def update_class(request):
    class_id = request.data.get("class_id")
    if not class_id:
        return Response({"error": "Missing class_id in request."}, status=400)
    
    try:
        teacher = Teacher.objects.get(user=request.user)
        classroom = Class.objects.get(id=class_id, teacher=teacher)
    except (Teacher.DoesNotExist, Class.DoesNotExist):
        return Response({"error": "Class not found or not yours."}, status=404)

    fields = ["name", "school_name", "school_address", "grade"]
    updated_fields = []

    for field in fields:
        if field in request.data:
            setattr(classroom, field, request.data[field])
            updated_fields.append(field)

    # Save basic class updates first
    classroom.save()

    # Handle lesson time updates
    lesson_times = request.data.get("lesson_times")
    if lesson_times is not None:
        if not isinstance(lesson_times, list):
            return Response({"error": "lesson_times must be a list of {day, time} objects."}, status=400)

        # Delete old ones
        classroom.lesson_times.all().delete()

        # Create new lesson times
        for entry in lesson_times:
            day = entry.get("day")
            time = entry.get("time")
            if day and time:
                LessonTime.objects.create(class_ref=classroom, day=day, time=time)

        updated_fields.append("lesson_times")

    return Response({
        "status": "Class updated",
        "updated_fields": updated_fields,
        "class_id": classroom.id
    }, status=200)



@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def class_detail(request, class_id):
    try:
        teacher = Teacher.objects.get(user=request.user)
        classroom = Class.objects.get(id=class_id, teacher=teacher)
    except (Teacher.DoesNotExist, Class.DoesNotExist):
        return Response({"error": "Class not found or not yours."}, status=404)

    # Overall class average
    overall_avg = (
        TermScore.objects
        .filter(student__classroom=classroom)
        .aggregate(avg=Avg("score"))["avg"]
    )

    # Average per term
    term_averages = (
        TermScore.objects
        .filter(student__classroom=classroom)
        .values("grade", "term")
        .annotate(avg_score=Avg("score"))
        .order_by("grade", "term")
    )

    return Response({
        "id": classroom.id,
        "name": classroom.name,
        "grade": classroom.grade,
        "school_name": classroom.school_name,
        "school_address": classroom.school_address,
        "code": classroom.code,
        "class_average": round(overall_avg, 2),
        "class_expectation": get_expectation_level(overall_avg),
        "term_score_averages": [
            {
                "grade": a["grade"],
                "term": a["term"],
                "average_score": round(a["avg_score"], 2) if a["avg_score"] else None,
                
            } for a in term_averages
        ]
    }, status=200)



@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def students_in_class(request, class_id):
    try:
        teacher = Teacher.objects.get(user=request.user)
        classroom = Class.objects.get(id=class_id, teacher=teacher)
    except (Teacher.DoesNotExist, Class.DoesNotExist):
        return Response({"error": "Class not found or not yours."}, status=404)

    students = classroom.students.prefetch_related("term_scores").all()

    # 🔍 Search filter
    search_query = request.GET.get("search")
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )

    # 🧠 Add student average as annotation (so we can order)
    students = students.annotate(avg_score=Avg("term_scores__score"))

    # ⬆️⬇️ Ordering
    ordering = request.GET.get("ordering")
    if ordering:
        if ordering.lstrip("-") in ["name", "avg_score"]:
            students = students.order_by(ordering)

    # 📄 Pagination
    paginator = GlobalPagination()
    page = paginator.paginate_queryset(students, request)

    student_data = []
    for student in page:
        scores = student.term_scores.all().values("grade", "term", "score").order_by("grade", "term")
        term_scores = [
            {
                "grade": s["grade"],
                "term": s["term"],
                "score": s["score"],
                "expectation": get_expectation_level(s["score"])
            }
            for s in scores
        ]
        student_data.append({
            "id": student.id,
            "name": student.name,
            "code": student.code,
            "term_scores": term_scores,
            "average_score": round(student.avg_score, 2) if student.avg_score else None,
            "average_expectation": get_expectation_level(student.avg_score) if student.avg_score else None
        })

    return paginator.get_paginated_response(student_data)


# ======================== TEACHER VIEWS ========================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def create_teacher(request):
    if Teacher.objects.filter(user=request.user).exists():
        return Response({"error": "Teacher profile already exists."}, status=400)
    
    phone_no = request.data.get("phone_no")
    if not phone_no:
        return Response({"error": "Phone number is required."}, status=400)

    teacher = Teacher.objects.create(
        user=request.user,
        phone_no=phone_no
    )

    return Response({
        "status": "Teacher profile created",
        "teacher_id": teacher.id
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsTeacher])
def update_teacher(request):
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return Response({"error": "Teacher profile not found."}, status=404)

    phone = request.data.get("phone_no")
    if phone:
        teacher.phone_no = phone
        teacher.save()
        return Response({"status": "Phone updated"})
    return Response({"error": "No phone number provided."}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def my_classes(request):
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return Response({"error": "Teacher profile not found."}, status=404)

    classes = teacher.classes.all()

    data = []
    for c in classes:
        lesson_times = c.lesson_times.all().values("day", "time")
        data.append({
            "id": c.id,
            "name": c.name,
            "grade": c.grade,
            "school_name": c.school_name,
            "school_address": c.school_address,
            "code": c.code,
            "lesson_times": list(lesson_times)
        })

    return Response(data, status=200)


# ======================== STUDENT VIEWS ========================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
@parser_classes([MultiPartParser])
def upload_students_csv(request):
    csv_file = request.FILES.get('file')
    class_id = request.POST.get("class_id")

    if not csv_file:
        return Response({"error": "No file uploaded."}, status=400)

    if not csv_file.name.endswith('.csv'):
        return Response({"error": "Only CSV files are supported."}, status=400)

    if not class_id:
        return Response({"error": "Missing class_id in request."}, status=400)

    # Get teacher and class
    try:
        teacher = Teacher.objects.get(user=request.user)
        classroom = Class.objects.get(id=class_id, teacher=teacher)
    except Teacher.DoesNotExist:
        return Response({"error": "Teacher profile not found."}, status=400)
    except Class.DoesNotExist:
        return Response({"error": "Class not found or not assigned to you."}, status=404)

    try:
        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        reader = csv.DictReader(io_string)
    except Exception as e:
        return Response({"error": f"Failed to parse CSV: {str(e)}"}, status=400)

    created_students = []

    for row in reader:
        name = row.get('student_name')
        if not name:
            continue

        student, _ = Student.objects.get_or_create(
            name=name,
            classroom=classroom,
            defaults={"code": generate_unique_code()}
        )
        created_students.append(student.name)

        for col, value in row.items():
            if not col:
                continue

            match = re.match(r"Grade(\d+)Term(\d+)Score", col)
            if match and value and value.strip():
                try:
                    grade = int(match.group(1))
                    term = int(match.group(2))
                    score = float(value.strip())
                    TermScore.objects.update_or_create(
                        student=student,
                        grade=grade,
                        term=term,
                        defaults={"score": score}
                    )
                except (ValueError, TypeError):
                    continue

    return Response({
        "status": "success",
        "created_students": created_students,
        "class": classroom.name,
        "grade": classroom.grade
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def upsert_term_scores(request):
    student_id = request.data.get("student_id")
    scores = request.data.get("scores", [])

    if not student_id or not isinstance(scores, list):
        return Response({"error": "Missing student_id or invalid scores list."}, status=400)

    try:
        student = Student.objects.get(id=student_id, classroom__teacher__user=request.user)
    except Student.DoesNotExist:
        return Response({"error": "Student not found or not in your class."}, status=404)

    result = []

    for entry in scores:
        grade = entry.get("grade")
        term = entry.get("term")
        score = entry.get("score")

        if not all([grade, term, score]):
            result.append({
                "grade": grade,
                "term": term,
                "status": "skipped",
                "reason": "Missing grade, term, or score"
            })
            continue

        term_score, created = TermScore.objects.update_or_create(
            student=student,
            grade=grade,
            term=term,
            defaults={"score": score}
        )

        result.append({
            "grade": grade,
            "term": term,
            "score": term_score.score,
            "status": "created" if created else "updated"
        })

    return Response({
        "student": student.name,
        "student_id": student.id,
        "results": result
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_term_scores(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({"error": "Student profile not found."}, status=404)

    scores = student.term_scores.all().order_by("grade", "term")
    score_list = []

    for score in scores:
        score_list.append({
            "grade": score.grade,
            "term": score.term,
            "score": score.score,
            "expectation": get_expectation_level(score.score)
        })

    # Average
    avg = scores.aggregate(avg=Avg("score"))["avg"]

    return Response({
        "student_id": student.id,
        "name": student.name,
        "code": student.code,
        "term_scores": score_list,
        "average_score": round(avg, 2) if avg else None,
        "average_expectation": get_expectation_level(avg) if avg else None
    }, status=200)