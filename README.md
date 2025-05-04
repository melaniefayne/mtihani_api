# Mtihani API

## Commands

```bash
source .venv/bin/activate && cd mtihaniapi 
python3 manage.py runserver

pip freeze > requirements.txt
django-admin startapp appName

python3 exam/mtihanigen/get_exam_curriculum.py

# migrations
python manage.py makemigrations && python manage.py migrate
python manage.py makemigrations learner && python manage.py migrate learner
python manage.py makemigrations exam && python manage.py migrate exam
python manage.py createsuperuser
```

## SetUp Process
- Create superusers
- Create system roles: admin, teacher, user
- Upload cbc JSONs
- Register teachers & classes & students (teacherOne: grade 7 & 8, teacherTwo: grade 9)
