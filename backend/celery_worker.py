from app import create_app
from app.extensions import celery

app = create_app()
app.app_context().push()

# Import tasks to register them
import app.tasks.snapshots       # noqa: F401
import app.tasks.monitors        # noqa: F401
import app.tasks.staleness       # noqa: F401
import app.tasks.maintenance     # noqa: F401
import app.tasks.notifications   # noqa: F401
