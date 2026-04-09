from app.extensions import celery
from app.models import Service, StatusSnapshot


@celery.task(name="app.tasks.snapshots.record_snapshots")
def record_snapshots():
    services = Service.objects(visible=True)
    count = 0
    for service in services:
        StatusSnapshot(service=service, status=service.status).save()
        count += 1
    return f"Recorded {count} snapshots"
