import mongoengine
from celery import Celery
from celery.schedules import crontab
import redis as redis_lib

celery = Celery(__name__)


def init_db(app):
    mongoengine.connect(host=app.config["MONGODB_SETTINGS"]["host"])


def init_redis(app):
    return redis_lib.from_url(app.config["REDIS_URL"])


def init_celery(app):
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        beat_schedule={
            "record-snapshots": {
                "task": "app.tasks.snapshots.record_snapshots",
                "schedule": crontab(minute="*/5"),
            },
            "run-due-monitors": {
                "task": "app.tasks.monitors.run_due_monitors",
                "schedule": crontab(minute="*"),  # every minute
            },
            "check-stale-services": {
                "task": "app.tasks.staleness.check_stale_services",
                "schedule": crontab(minute="*"),  # every minute
            },
            "check-maintenance-windows": {
                "task": "app.tasks.maintenance.check_maintenance_windows",
                "schedule": crontab(minute="*"),  # every minute
            },
        },
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
