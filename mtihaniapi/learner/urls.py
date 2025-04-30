from django.urls import path
from .views import create_classroom, get_user_classrooms

urlpatterns = [
    path('create-class', create_classroom),
    path('get-user-classrooms', get_user_classrooms),
    # path('create_teacher', create_teacher),
    # path('upload_students', upload_students_csv),
    # path('update_class', update_class),
    # path('update_teacher', update_teacher),
    # path('update_term_scores', upsert_term_scores),
    # path('my_classes', my_classes),
    # path('class_detail/<int:class_id>', class_detail),
    # path('students_in_class/<int:class_id>', students_in_class),
    # path('my_term_scores', my_term_scores),
]
