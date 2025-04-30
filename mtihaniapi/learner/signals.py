# learner/signals.py

from django.contrib.auth.models import User

def is_teacher(self):
    return hasattr(self, 'teacher')

def is_student(self):
    return hasattr(self, 'student')

User.add_to_class('is_teacher', property(is_teacher))
User.add_to_class('is_student', property(is_student))