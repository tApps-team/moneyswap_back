import os

from celery import Celery
from kombu import Queue

from config import REDIS_URL


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

app.conf.ONCE = {
  'backend': 'celery_once.backends.Redis',
  'settings': {
    'url': REDIS_URL,
    'default_timeout': 60 * 10,
    'delete_after_success': True,
  }
}

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.broker_transport_options = {'visibility_timeout': 1800}

app.autodiscover_tasks()


# app.conf.task_queues = (
#     Queue('cpu_queue'),       # очередь для CPU-задач
#     Queue('io_queue'),      # очередь для I/O задач
# )