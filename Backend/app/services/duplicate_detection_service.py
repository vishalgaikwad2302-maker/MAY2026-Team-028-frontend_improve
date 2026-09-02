"""Duplicate detection service for complaints."""

import math
import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.complaint import Complaint
from app.repositories.complaint_repository import ComplaintRepository

__all__ = ["DuplicateDetectionService"]


class DuplicateDetectionService:
    _STOPWORDS = {
        "the",
        "a",
        "an",
        "near",
        "of",
        "at",
        "in",
        "on",
        "for",
        "and",
        "to",
        "is",
        "was",
        "were",
        "it",
        "this",
        "that",
        "with",
        "by",
    }

    @staticmethod
    def _tokenize(text: str | None) -> set[str]:
        raw = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
        return {
            word
            for word in raw.split()
            if len(word) > 1 and word not in DuplicateDetectionService._STOPWORDS
        }

    @staticmethod
    def _text_similarity(a: str | None, b: str | None) -> float:
        set_a = DuplicateDetectionService._tokenize(a)
        set_b = DuplicateDetectionService._tokenize(b)
        if not set_a or not set_b:
            return 0.0
        overlap = len(set_a & set_b)
        union = len(set_a | set_b)
        return overlap / union if union else 0.0

    @staticmethod
    def _distance_meters(
        a: tuple[float, float] | None, b: tuple[float, float] | None
    ) -> float | None:
        if not a or not b:
            return None
        lat1, lng1 = a
        lat2, lng2 = b
        radius = 6371000
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        sin_lat = math.sin(d_lat / 2) ** 2
        sin_lng = math.sin(d_lng / 2) ** 2
        h = sin_lat + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * sin_lng
        return 2 * radius * math.asin(math.sqrt(h))

    @staticmethod
    def find_possible_duplicates(db: Session, complaint: Complaint) -> list[dict]:
        candidates, _ = ComplaintRepository.list(db, filters={"page": 1, "page_size": 500})
        active = [
            c for c in candidates if c.id != complaint.id and c.status in {"pending", "in_progress"}
        ]
        matches: list[dict] = []
        draft_coords = (
            (complaint.latitude, complaint.longitude)
            if complaint.latitude and complaint.longitude
            else None
        )
        for item in active:
            item_coords = (
                (item.latitude, item.longitude) if item.latitude and item.longitude else None
            )
            dist = DuplicateDetectionService._distance_meters(draft_coords, item_coords)
            location_score = DuplicateDetectionService._text_similarity(complaint.title, item.title)
            desc_score = DuplicateDetectionService._text_similarity(
                complaint.description, item.description
            )
            is_nearby = dist is not None and dist <= settings.duplicate_radius_meters
            is_duplicate = (
                is_nearby
                or location_score >= settings.duplicate_text_similarity_threshold
                or (
                    location_score >= settings.duplicate_score_threshold
                    and desc_score >= settings.duplicate_score_threshold
                )
            )
            if not is_duplicate:
                continue
            matches.append(
                {
                    "complaint": item,
                    "distance": dist,
                    "locationScore": location_score,
                    "descScore": desc_score,
                    "confidence": (0.5 if is_nearby else 0.0)
                    + (location_score * 0.3)
                    + (desc_score * 0.2),
                }
            )
        return sorted(matches, key=lambda match: match["confidence"], reverse=True)
