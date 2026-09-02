"""Database initialization and seeding of demo users."""

import logging
from datetime import datetime

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app import models as _models
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.models.collection_schedule import CollectionFrequency, CollectionSchedule
from app.models.user import User, UserRole
from app.models.ward import Ward
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

DEMO_USERS_SEED = [
    {
        "username": "citizen",
        "email": "citizen@smartsweep.gov",
        "password": "citizen123",
        "full_name": "Sagnik Halder",
        "role": UserRole.CITIZEN.value,
    },
    {
        "username": "anita",
        "email": "anita@smartsweep.gov",
        "password": "anita123",
        "full_name": "Anita Rao",
        "role": UserRole.CITIZEN.value,
    },
    {
        "username": "mohammed",
        "email": "mohammed@smartsweep.gov",
        "password": "mohammed123",
        "full_name": "Mohammed Iqbal",
        "role": UserRole.CITIZEN.value,
    },
    {
        "username": "crew",
        "email": "crew@smartsweep.gov",
        "password": "crew123",
        "full_name": "Suresh Patil",
        "role": UserRole.CREW.value,
    },
    {
        "username": "admin",
        "email": "admin@smartsweep.gov",
        "password": "admin123",
        "full_name": "Ward Supervisor / Admin",
        "role": UserRole.ADMIN.value,
    },
]

DEMO_WARDS_SEED = [
    {"name": "MG Road (Ward 04)"},
    {"name": "Indiranagar (Ward 12)"},
    {"name": "Koramangala (Ward 08)"},
    {"name": "Jayanagar (Ward 15)"},
]

DEMO_SCHEDULES_SEED = [
    # MG Road (Ward 04) - ward_id 1
    {"ward_idx": 0, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 0, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 0, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 2, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 0, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 4, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 0, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 1, "notes": "Dry Waste", "time_slot": "Morning"},
    {"ward_idx": 0, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 5, "notes": "Dry Waste", "time_slot": "Morning"},
    {"ward_idx": 0, "frequency": CollectionFrequency.MONTHLY.value, "day_of_week": 5, "week_of_month": 0, "notes": "Hazardous / E-Waste", "time_slot": "Morning"},

    # Indiranagar (Ward 12) - ward_id 2
    {"ward_idx": 1, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 0, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 1, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 2, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 1, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 4, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 1, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 3, "notes": "Dry Waste", "time_slot": "Morning"},
    {"ward_idx": 1, "frequency": CollectionFrequency.MONTHLY.value, "day_of_week": 6, "week_of_month": 0, "notes": "Hazardous / E-Waste", "time_slot": "Morning"},

    # Koramangala (Ward 08) - ward_id 3
    {"ward_idx": 2, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 1, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 2, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 3, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 2, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 5, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 2, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 0, "notes": "Dry Waste", "time_slot": "Morning"},
    {"ward_idx": 2, "frequency": CollectionFrequency.MONTHLY.value, "day_of_week": 5, "week_of_month": 2, "notes": "Hazardous / E-Waste", "time_slot": "Morning"},

    # Jayanagar (Ward 15) - ward_id 4
    {"ward_idx": 3, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 6, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 3, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 1, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 3, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 3, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 3, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 5, "notes": "Wet Waste", "time_slot": "Morning"},
    {"ward_idx": 3, "frequency": CollectionFrequency.WEEKLY.value, "day_of_week": 2, "notes": "Dry Waste", "time_slot": "Morning"},
    {"ward_idx": 3, "frequency": CollectionFrequency.MONTHLY.value, "day_of_week": 6, "week_of_month": 2, "notes": "Hazardous / E-Waste", "time_slot": "Morning"},
]

DEMO_EXCEPTIONS_SEED = [
    {"exception_date": "2026-08-15", "notes": "Independence Day — no collection. Pickup shifts to the next working day."},
    {"exception_date": "2026-08-29", "notes": "Ganesh Chaturthi — dry waste collection only; wet waste resumes the day after."},
]



def _migrate_missing_columns() -> None:
    """Inspect all declared models and dynamically add any missing columns to existing tables."""
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if table_name not in existing_tables:
                    continue
                existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
                for column in table.columns:
                    if column.name not in existing_columns:
                        col_type = column.type.compile(engine.dialect)
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
                        logger.info("Applying auto-migration: %s", sql)
                        try:
                            conn.execute(text(sql))
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "Auto-migration note for %s.%s (%s): %s",
                                table_name,
                                column.name,
                                sql,
                                exc,
                            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Auto-migration inspector encountered an error: %s", exc)


def init_db(db: Session) -> None:
    """Ensure database tables exist and seed initial demo users, wards, and schedules."""
    _ = _models.__all__
    Base.metadata.create_all(bind=engine)
    _migrate_missing_columns()

    for user_data in DEMO_USERS_SEED:
        existing = UserRepository.get_by_email(db, user_data["email"])
        if not existing:
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True,
            )
            UserRepository.create(db, user)
            logger.info("Seeded demo user: %s (%s)", user_data["full_name"], user_data["email"])

    # Seed wards and schedules
    ward_objs = []
    for ward_data in DEMO_WARDS_SEED:
        existing_ward = db.query(Ward).filter(Ward.name == ward_data["name"]).first()
        if not existing_ward:
            ward = Ward(name=ward_data["name"])
            db.add(ward)
            db.commit()
            db.refresh(ward)
            ward_objs.append(ward)
            logger.info("Seeded demo ward: %s", ward.name)
        else:
            ward_objs.append(existing_ward)

    if not db.query(CollectionSchedule).first() and ward_objs:
        for sched in DEMO_SCHEDULES_SEED:
            ward = ward_objs[sched["ward_idx"]]
            cs = CollectionSchedule(
                ward_id=ward.id,
                frequency=sched["frequency"],
                day_of_week=sched.get("day_of_week"),
                week_of_month=sched.get("week_of_month"),
                time_slot=sched.get("time_slot"),
                notes=sched.get("notes"),
                is_exception=False
            )
            db.add(cs)
        
        for ward in ward_objs:
            for exc in DEMO_EXCEPTIONS_SEED:
                cs = CollectionSchedule(
                    ward_id=ward.id,
                    is_exception=True,
                    exception_date=datetime.strptime(exc["exception_date"], "%Y-%m-%d").date(),
                    notes=exc["notes"]
                )
                db.add(cs)
        
        db.commit()
        logger.info("Seeded demo schedules and exceptions.")
