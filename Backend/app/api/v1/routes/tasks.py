"""Task API routes."""

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.task import Task
from app.models.user import User, UserRole
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskComplete, TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _to_read_model(task: Task, db: Session) -> TaskRead:
    read = TaskRead.model_validate(task)
    read.worker_ids = TaskRepository.get_worker_ids(db, task.id) if task.id else []
    read.equipment_ids = TaskRepository.get_equipment_ids(db, task.id) if task.id else []
    return read


@router.get(
    "",
    response_model=list[TaskRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
)
def list_tasks(db: Session = Depends(get_db)) -> list[TaskRead]:
    tasks = TaskRepository.list(db)
    return [_to_read_model(task, db) for task in tasks]


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = TaskService.create_task(db, current_user, task_in)
    return _to_read_model(task, db)


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskRead:
    return _to_read_model(TaskService.get_task(db, task_id), db)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)) -> TaskRead:
    return _to_read_model(TaskService.update_task(db, task_id, task_in), db)


@router.post(
    "/{task_id}/complete",
    response_model=TaskRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
)
def complete_task(
    task_id: int,
    payload: TaskComplete | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return _to_read_model(
        TaskService.complete_task(
            db,
            task_id,
            completed_by_user_id=current_user.id,
            completion_photo_url=payload.completion_photo_url if payload else None,
            waste_removed=payload.waste_removed if payload else None,
            resolution_notes=payload.resolution_notes if payload else None,
        ),
        db,
    )


@router.post(
    "/{task_id}/cancel",
    response_model=TaskRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def cancel_task(task_id: int, db: Session = Depends(get_db)) -> TaskRead:
    return _to_read_model(TaskService.cancel_task(db, task_id), db)
