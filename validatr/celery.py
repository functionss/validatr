import os
import celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "validatr.api.settings")


celery_app = celery.Celery("validatr")

celery_app.config_from_object(
    "django.conf:settings",
    namespace="validatr",
),
celery_app.autodiscover_tasks()
