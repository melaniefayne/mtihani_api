# mtihaniapi/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mtihaniapi.settings')

app = Celery('mtihaniapi')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks inside all installed apps' tasks.py files
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')