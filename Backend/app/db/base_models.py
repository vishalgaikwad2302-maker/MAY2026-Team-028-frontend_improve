"""Model import aggregator — the module Alembic imports.

Task S1-F08 support. This file exists for exactly one reason: SQLAlchemy only
knows about a table once the module defining it has been imported. Alembic's
``--autogenerate`` diffs ``Base.metadata`` against the live database, so any
model whose module was never imported looks like a table that "should be
dropped".

**Every new model module must be added below.** If a migration autogenerates a
surprising ``op.drop_table``, a missing import here is the first thing to check.

Kept separate from ``base.py`` to break the import cycle: models import ``Base``
from ``base``, so ``base`` cannot import models.
"""

from app.db.base import Base  # noqa: F401  (re-exported for Alembic's target_metadata)

# Sprint 1 models (migration 0001) + Sprint 2 models (migration 0003), one
# sorted block so `ruff --fix` has nothing left to reorder.
from app.models.bulk_pickup import BulkPickup  # noqa: F401
from app.models.collection_schedule import CollectionSchedule  # noqa: F401
from app.models.complaint import Complaint, ComplaintStatusHistory  # noqa: F401
from app.models.equipment import Equipment  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.task import Task, task_equipment, task_workers  # noqa: F401
from app.models.transparency import PostComment, TransparencyPost  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.models.ward import Ward  # noqa: F401
from app.models.worker import Worker  # noqa: F401

__all__ = ["Base"]
