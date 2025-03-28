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
from utils import generate_unique_code


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
