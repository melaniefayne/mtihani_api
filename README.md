# Mtihani API

## Commands

```bash
source .venv/bin/activate && cd mtihaniapi
python3 manage.py runserver
redis-server
celery -A mtihaniapi worker --loglevel=info

pip freeze > requirements.txt
django-admin startapp appName

python3 gen/curriculum.py

lsof -i :6379
kill 3180

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


## Notes
- Make the language simpler!

10 Elijah Kibet - 44.8
9 Sharon Njeri - 67.2
8 Wycliffe Mwangi - 75.0
7 Aisha Ali - 97.0
6 Moses Kipkoech - 54.2
5 Linet Cherono - 86.4
4 Brian Otieno - 50.2
3 Faith Mwikali - 93.4
2 Kevin Omondi - 65.0
1 Grace Wanjiru - 84.2