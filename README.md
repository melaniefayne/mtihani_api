# Mtihani API

## Commands

```bash
source .venv/bin/activate
pip freeze > requirements.txt
django-admin startapp appName
python3 manage.py runserver
python manage.py makemigrations learner && python manage.py migrate learner
python manage.py createsuperuser                                   
```

## SetUp Process
- Create superusers
- Create system roles: admin, teacher, user
- Upload cbc JSONs
- Register teachers & classes & students (teacherOne: grade 7 & 8, teacherTwo: grade 9)