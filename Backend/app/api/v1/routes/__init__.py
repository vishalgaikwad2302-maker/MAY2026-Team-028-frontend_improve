"""Resource route modules (one per aggregate)."""

from app.api.v1.routes import auth, complaints, resources, tasks, wards

__all__ = ["auth", "complaints", "resources", "tasks", "wards"]
