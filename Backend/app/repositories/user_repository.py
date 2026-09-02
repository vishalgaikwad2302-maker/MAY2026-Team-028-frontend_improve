"""User repository for database operations on User model."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

__all__ = ["UserRepository"]


class UserRepository:
    """Handles CRUD operations for the User entity."""

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        """Fetch a single user by ID."""
        return db.get(User, user_id)

    @staticmethod
    def get_by_email(db: Session, email_or_username: str) -> User | None:
        """Fetch a single user by lowercased email or username."""
        clean = email_or_username.lower().strip()
        stmt = select(User).where((User.email == clean) | (User.email == f"{clean}@smartsweep.gov"))
        return db.scalar(stmt)

    @staticmethod
    def create(db: Session, user: User) -> User:
        """Persist a new User entity to the database."""
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update(db: Session, user: User, update_data: dict[str, Any]) -> User:
        """Update an existing User entity fields."""
        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return user
