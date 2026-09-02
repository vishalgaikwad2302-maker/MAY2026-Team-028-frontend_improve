"""Collection schedule service (S2-F04, US-32/US-33).

Ports the nth-weekday-of-month math from
``Frontend/src/utils/collectionSchedule.js`` to compute reminders server-side.
Biweekly rows have no stored anchor date to know which of the two weeks is
"on", so they are reminded on the same next-matching-weekday basis as weekly
rows — a known simplification, not a precise fortnightly cadence.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.collection_schedule import CollectionSchedule
from app.repositories.collection_schedule_repository import CollectionScheduleRepository
from app.schemas.collection_schedule import (
    CollectionScheduleCreate,
    CollectionScheduleUpdate,
    ScheduleReminderRead,
)

__all__ = ["CollectionScheduleService"]


def _next_weekly_occurrence(from_date: date, day_of_week: int) -> date:
    days_ahead = (day_of_week - from_date.weekday()) % 7
    return from_date + timedelta(days=days_ahead)


def _monthly_date_for(year: int, month: int, day_of_week: int, week_of_month: int) -> date:
    first = date(year, month, 1)
    days_until_target = (day_of_week - first.weekday()) % 7
    return first + timedelta(days=days_until_target + week_of_month * 7)


def _next_monthly_occurrence(from_date: date, day_of_week: int, week_of_month: int) -> date:
    candidate = _monthly_date_for(from_date.year, from_date.month, day_of_week, week_of_month)
    if candidate < from_date:
        year, month = from_date.year, from_date.month + 1
        if month > 12:
            month, year = 1, year + 1
        candidate = _monthly_date_for(year, month, day_of_week, week_of_month)
    return candidate


class CollectionScheduleService:
    @staticmethod
    def create_schedule(db: Session, schedule_in: CollectionScheduleCreate) -> CollectionSchedule:
        schedule = CollectionSchedule(
            ward_id=schedule_in.ward_id,
            frequency=schedule_in.frequency.value,
            day_of_week=schedule_in.day_of_week,
            week_of_month=schedule_in.week_of_month,
            time_slot=schedule_in.time_slot,
            is_exception=schedule_in.is_exception,
            exception_date=schedule_in.exception_date,
            notes=schedule_in.notes,
        )
        return CollectionScheduleRepository.create(db, schedule)

    @staticmethod
    def get_schedule_row(db: Session, schedule_id: int) -> CollectionSchedule:
        schedule = CollectionScheduleRepository.get_by_id(db, schedule_id)
        if not schedule:
            raise NotFoundError("Collection schedule row not found.")
        return schedule

    @staticmethod
    def update_schedule(
        db: Session, schedule_id: int, update_in: CollectionScheduleUpdate
    ) -> CollectionSchedule:
        schedule = CollectionScheduleService.get_schedule_row(db, schedule_id)
        update_data = update_in.model_dump(exclude_unset=True)
        frequency = update_data.get("frequency")
        if frequency is not None:
            update_data["frequency"] = frequency.value if hasattr(frequency, "value") else frequency
        return CollectionScheduleRepository.update(db, schedule, update_data)

    @staticmethod
    def delete_schedule(db: Session, schedule_id: int) -> None:
        schedule = CollectionScheduleService.get_schedule_row(db, schedule_id)
        CollectionScheduleRepository.delete(db, schedule)

    @staticmethod
    def get_ward_schedule(db: Session, ward_id: int) -> list[CollectionSchedule]:
        return CollectionScheduleRepository.list_by_ward(db, ward_id)

    @staticmethod
    def get_reminders(
        db: Session, ward_id: int, *, today: date | None = None
    ) -> list[ScheduleReminderRead]:
        """One computed next-occurrence reminder per regular schedule row for a ward."""
        today = today or date.today()
        reminders: list[ScheduleReminderRead] = []
        for row in CollectionScheduleRepository.list_by_ward(db, ward_id):
            if row.is_exception:
                if row.exception_date is not None and row.exception_date >= today:
                    reminders.append(
                        ScheduleReminderRead(
                            schedule_id=row.id,
                            ward_id=row.ward_id,
                            occurrence_date=row.exception_date,
                            time_slot=row.time_slot,
                            is_exception=True,
                            notes=row.notes,
                        )
                    )
                continue

            if row.day_of_week is None:
                continue
            if row.week_of_month is not None:
                occurrence = _next_monthly_occurrence(today, row.day_of_week, row.week_of_month)
            else:
                occurrence = _next_weekly_occurrence(today, row.day_of_week)

            reminders.append(
                ScheduleReminderRead(
                    schedule_id=row.id,
                    ward_id=row.ward_id,
                    occurrence_date=occurrence,
                    time_slot=row.time_slot,
                    is_exception=False,
                    notes=row.notes,
                )
            )

        reminders.sort(key=lambda r: r.occurrence_date)
        return reminders
