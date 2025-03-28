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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
    if not csv_file:
        return Response({"error": "No file uploaded."}, status=400)

    if not csv_file.name.endswith('.csv'):
        return Response({"error": "Only CSV files are supported."}, status=400)

    try:
        teacher = Teacher.objects.get(user=request.user)
        classroom = Class.objects.filter(teacher=teacher).first()
        if not classroom:
            return Response({"error": "No class found for this teacher."}, status=400)
    except Teacher.DoesNotExist:
        return Response({"error": "Teacher profile not found."}, status=400)

    data_set = csv_file.read().decode('UTF-8')
    io_string = io.StringIO(data_set)
    reader = csv.DictReader(io_string)

    created_students = []

    for row in reader:
        name = row.get('student_name')
        if not name:
            continue

        student = Student.objects.create(
            name=name,
            code=generate_unique_code(),
            classroom=classroom
        )
        created_students.append(student.name)

        for col, value in row.items():
            match = re.match(r"Grade(\d+)Term(\d+)Score", col)
            if match and value.strip():
                grade = int(match.group(1))
                term = int(match.group(2))
                try:
                    score = float(value.strip())
                    TermScore.objects.create(
                        student=student,
                        grade=grade,
                        term=term,
                        score=score
                    )
                except ValueError:
                    continue

    return Response({
        "status": "success",
        "created_students": created_students
    }, status=201)
