from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import Group
from rest_framework.status import *
from learner.models import Student, Teacher
from django.db.models import Q


@api_view(['POST'])
def register_user(request):
    try:
        email = request.data.get("email")
        password = request.data.get("password")
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        name = f"{first_name} {last_name}".strip()
        role = request.data.get("role")
        phone_no = request.data.get("phone_no")
        student_code = request.data.get("student_code")

        if not role or role not in ['admin', 'teacher', 'student']:
            return Response({"message": "Invalid or missing role."}, status=HTTP_400_BAD_REQUEST)

        if User.objects.filter(Q(username=email) | Q(email=email)).exists():
            return Response({"message": "User email already exists"}, status=HTTP_400_BAD_REQUEST)

        student_record = None
        if role == 'student':
            if not student_code:
                return Response({"message": "Missing student_code for student registration."}, status=HTTP_400_BAD_REQUEST)
            try:
                student_record = Student.objects.get(code=student_code)
                if student_record.user is not None:
                    return Response({"message": "This student code has already been registered."}, status=HTTP_400_BAD_REQUEST)
            except Student.DoesNotExist:
                return Response({"message": "Invalid student code. No matching student found."}, status=HTTP_404_NOT_FOUND)

        user = User.objects.create_user(
            username=email, email=email, password=password,
            first_name=student_record.name if role == "student" else name
        )

        group, _ = Group.objects.get_or_create(name=role)
        group.user_set.add(user)

        teacher_id = None

        if role == 'student' and student_record:
            student_record.user = user
            student_record.status = "Active"
            student_record.save()

        elif role == 'teacher':
            teacher = Teacher.objects.create(
                user=user, name=name, phone_no=phone_no)
            teacher_id = teacher.id

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Account created successfully",
            "user": {
                "user_id": user.id,
                "email": user.email,
                "name": user.first_name,
                "role": role,
                "teacher_id": teacher_id,
                "phone_no": phone_no,
            },
            "token": str(refresh.access_token),
        }, status=HTTP_201_CREATED)

    except Exception as e:
        print(f"Error during registration: {e}")
        return Response({"message": "Something went wrong. Please try again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def login_user(request):
    try:
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"message": "Email and password are required."}, status=HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "User with this email does not exist."}, status=HTTP_401_UNAUTHORIZED)

        user = authenticate(username=email, password=password)

        if user is None:
            return Response({"message": "Invalid credentials."}, status=HTTP_401_UNAUTHORIZED)

        if user.is_superuser or user.groups.filter(name="admin").exists():
            return Response({"message": "Invalid role on app login."}, status=HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        user_details = get_user_details(user)

        if user_details is None:
            return Response({"message": "Error fetching user details."}, status=HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Login successful. Welcome back",
            "user": user_details,
            "token": str(refresh.access_token),
        }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please try again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


def get_user_details(user):
    try:
        teacher_id = None
        phone_no = None
        created_at = None
        updated_at = None
        role = "unknown"

        if user.groups.filter(name="teacher").exists():
            role = "teacher"
            try:
                teacher = Teacher.objects.get(user=user)
                teacher_id = teacher.id
                phone_no = teacher.phone_no
                created_at = teacher.created_at
                updated_at = teacher.updated_at
            except Teacher.DoesNotExist:
                pass

        elif user.groups.filter(name="student").exists():
            role = "student"

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.first_name,
            "role": role,
            "teacher_id": teacher_id,
            "phone_no": phone_no,
            "created_at": created_at,
            "updated_at": updated_at,
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user(request):
    try:
        user = request.user
        email = request.data.get("email")
        name = request.data.get("first_name") + ' ' + \
            request.data.get("last_name")
        phone_no = request.data.get("phone_no")

        if email:
            if User.objects.exclude(id=user.id).filter(email=email).exists():
                return Response({"message": "A user with this email already exists"}, status=HTTP_400_BAD_REQUEST)
            user.email = email
            user.username = email

        if name:
            user.first_name = name

        if phone_no:
            if user.groups.filter(name="teacher").exists():
                try:
                    teacher = Teacher.objects.get(user=user)
                    teacher.phone_no = phone_no
                    teacher.save()
                except Teacher.DoesNotExist:
                    return Response({"message": "Teacher account not found."}, status=HTTP_400_BAD_REQUEST)

        user.save()

        user_details = get_user_details(user)

        if user_details is None:
            return Response({"message": "Error fetching user details."}, status=HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Profile updated successfully",
            "new_user": user_details,
        }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please ty again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    try:
        user = request.user
        current = request.data.get("current_password")
        new = request.data.get("new_password")

        if not user.check_password(current):
            return Response({"message": "Current password is incorrect."}, status=HTTP_400_BAD_REQUEST)

        user.set_password(new)
        user.save()
        return Response({"status": "Password changed successfully"})
    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please ty again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)
