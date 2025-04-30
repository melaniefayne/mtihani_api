import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from models import Classroom, ClassroomStudent, Teacher, User


@pytest.mark.django_db
def test_get_teacher_classrooms_returns_data_for_teacher():
    teacher_user = User.objects.create_user(username='teach', password='pass')
    teacher = Teacher.objects.create(user=teacher_user, name="Mr. T")

    classroom = Classroom.objects.create(
        name="7A", subject="Science", grade=7,
        school_name="Test School", school_address="123 St",
        teacher=teacher
    )

    client = APIClient()
    client.force_authenticate(user=teacher_user)

    response = client.get(reverse('get-user-classrooms'))  # use actual name in urls.py

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['id'] == classroom.id
    assert 'avg_term_score' in response.data[0]
    assert 'lesson_times' in response.data[0]


@pytest.mark.django_db
def test_get_student_classrooms_returns_data_for_student():
    student_user = User.objects.create_user(username='stud', password='pass')
    student = ClassroomStudent.objects.create(user=student_user, name="Alex")

    classroom = Classroom.objects.create(
        name="7A", subject="Science", grade=7,
        school_name="Test School", school_address="123 St",
    )
    student.classrooms.add(classroom)

    client = APIClient()
    client.force_authenticate(user=student_user)

    response = client.get(reverse('get-user-classrooms'))

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['id'] == classroom.id
    assert 'avg_mtihani_score' in response.data[0]
    assert 'term_scores' in response.data[0]