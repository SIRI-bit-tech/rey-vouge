import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rey_vogue.settings')

app = Celery('rey_vogue')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure Celery Beat schedule
app.conf.beat_schedule = {
    'process-abandoned-carts': {
        'task': 'orders.tasks.process_abandoned_carts',
        'schedule': crontab(hour='*/6'),  # Run every 6 hours
    },
}

app.conf.timezone = 'UTC'

# Configure task routes
app.conf.task_routes = {
    'orders.tasks.*': {'queue': 'orders'},
    'core.tasks.*': {'queue': 'default'},
}

# Configure task settings
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.task_time_limit = 5 * 60  # 5 minutes
app.conf.task_soft_time_limit = 60  # 1 minute
app.conf.worker_prefetch_multiplier = 1  # One task per worker

# Configure Redis settings
app.conf.broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Error handling
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 