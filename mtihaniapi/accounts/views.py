from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Group

from learner.models import Teacher, Student
from learner.serializers import TeacherSerializer


@api_view(['POST'])
def register_user(request):
    email = request.data.get("email")
    password = request.data.get("password")
    name = request.data.get("first_name") + ' ' + request.data.get("last_name")
    role = request.data.get("role")
    student_code = request.data.get("student_code")

    if not role or role not in ['admin', 'teacher', 'student']:
        return Response({"error": "Invalid or missing role."}, status=400)

    if User.objects.filter(username=email).exists():
        return Response({"error": "User already exists"}, status=400)

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name
    )

    group, _ = Group.objects.get_or_create(name=role)
    group.user_set.add(user)

    if role == 'student':
        if not student_code:
            return Response({"error": "Student code is required for student registration."}, status=400)

        try:
            student = Student.objects.get(code=student_code)
        except Student.DoesNotExist:
            return Response({"error": "Invalid student code."}, status=400)

        if student.user is not None:
            return Response({"error": "This student code has already been used."}, status=400)

        student.user = user
        student.save()

    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.first_name,
            "role": role,
        }
    }, status=201)


@api_view(['POST'])
def login_user(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Email and password are required."}, status=400)

    user = authenticate(username=email, password=password)

    if user is None:
        return Response({"error": "Invalid credentials."}, status=401)

    refresh = RefreshToken.for_user(user)

    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.first_name,
    }

    role = "unknown"
    profile_data = {}

    if user.groups.filter(name="teacher").exists():
        role = "teacher"
        try:
            teacher = Teacher.objects.get(user=user)
            profile_data = TeacherSerializer(teacher).data
        except Teacher.DoesNotExist:
            profile_data = {"error": "Teacher profile not found."}

    elif user.groups.filter(name="student").exists():
        role = "student"
        # Add StudentSerializer logic later

    elif user.is_superuser or user.groups.filter(name="admin").exists():
        role = "admin"

    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": user_data,
        "role": role,
        "profile": profile_data
    }, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user(request):
    user = request.user
    email = request.data.get("email")
    name = request.data.get("first_name") + ' ' + request.data.get("last_name")

    if email:
        if User.objects.exclude(id=user.id).filter(email=email).exists():
            return Response({"error": "Email already in use."}, status=400)
        user.email = email
        user.username = email

    if name:
        user.first_name = name

    user.save()
    return Response({"status": "User updated"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current = request.data.get("current_password")
    new = request.data.get("new_password")

    if not user.check_password(current):
        return Response({"error": "Current password is incorrect."}, status=400)

    user.set_password(new)
    user.save()
    return Response({"status": "Password changed successfully"})