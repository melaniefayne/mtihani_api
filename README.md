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

# commands
python manage.py export_exam_performance exam_id
```
