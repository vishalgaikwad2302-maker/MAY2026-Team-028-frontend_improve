"""Claude-powered hazard classification and 3-tag image/condition labeling (US-28/29/30).

Uses Anthropic's minimal, lightweight vision model (claude-3-haiku-20240307)
to classify complaints and assign the top 3 matching condition tags from a rich
predefined taxonomy, with a deterministic keyword-based heuristic fallback.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.complaint import Complaint, ComplaintCategory
from app.repositories.complaint_repository import ComplaintRepository

__all__ = ["ClassificationResult", "ComplaintClassificationService", "PREDEFINED_TAGS"]

logger = logging.getLogger(__name__)

_CLAUDE_MODEL = "claude-3-haiku-20240307"

PREDEFINED_TAGS: list[str] = [
    "Overflowing Garbage Bin",
    "Plastic Waste & Bottles",
    "Stagnant Dirty Water",
    "Mosquito Breeding Risk",
    "Roadside Street Litter",
    "Construction & Demolition Debris",
    "Clogged Drain / Sewer Overflow",
    "Hazardous Chemical / Toxic Waste",
    "Medical & Biohazard Waste",
    "Foul Odor & Decomposing Garbage",
    "E-Waste & Broken Electronics",
    "Bulk Furniture & Old Mattresses",
    "Tree Branches & Garden Waste",
    "Animal Waste & Carcass",
    "Illegal Open Dumping Site",
    "Broken Glass & Sharp Metal",
    "Market & Vegetable Waste",
    "Industrial Scrap Material",
    "Cardboard & Paper Waste",
    "Food Waste & Kitchen Leftovers",
    "Damaged Pavement / Road Hazard",
    "Open Manhole & Broken Cover",
    "Public Park & Playground Litter",
    "Water Pipe Leakage",
    "Discarded Tyres & Rubber",
    "Scattered Dry Leaves / Biomass",
]

_KEYWORD_RULES: list[tuple[str, ComplaintCategory]] = [
    ("mosquito", ComplaintCategory.MOSQUITO_BREEDING),
    ("stagnant water", ComplaintCategory.MOSQUITO_BREEDING),
    ("standing water", ComplaintCategory.MOSQUITO_BREEDING),
    ("child", ComplaintCategory.RISK_TO_CHILDREN),
    ("school", ComplaintCategory.RISK_TO_CHILDREN),
    ("playground", ComplaintCategory.RISK_TO_CHILDREN),
    ("smell", ComplaintCategory.FOUL_SMELL),
    ("odor", ComplaintCategory.FOUL_SMELL),
    ("odour", ComplaintCategory.FOUL_SMELL),
    ("stench", ComplaintCategory.FOUL_SMELL),
    ("overflow", ComplaintCategory.OVERFLOWING_BIN),
    ("bin full", ComplaintCategory.OVERFLOWING_BIN),
    ("spilling", ComplaintCategory.OVERFLOWING_BIN),
]

_KEYWORD_TAG_RULES: list[tuple[str, str]] = [
    ("mosquito", "Mosquito Breeding Risk"),
    ("stagnant", "Stagnant Dirty Water"),
    ("standing water", "Stagnant Dirty Water"),
    ("plastic", "Plastic Waste & Bottles"),
    ("bottle", "Plastic Waste & Bottles"),
    ("overflow", "Overflowing Garbage Bin"),
    ("bin full", "Overflowing Garbage Bin"),
    ("spill", "Overflowing Garbage Bin"),
    ("dustbin", "Overflowing Garbage Bin"),
    ("litter", "Roadside Street Litter"),
    ("road", "Roadside Street Litter"),
    ("street", "Roadside Street Litter"),
    ("construction", "Construction & Demolition Debris"),
    ("debris", "Construction & Demolition Debris"),
    ("cement", "Construction & Demolition Debris"),
    ("rubble", "Construction & Demolition Debris"),
    ("drain", "Clogged Drain / Sewer Overflow"),
    ("gutter", "Clogged Drain / Sewer Overflow"),
    ("sewer", "Clogged Drain / Sewer Overflow"),
    ("smell", "Foul Odor & Decomposing Garbage"),
    ("odor", "Foul Odor & Decomposing Garbage"),
    ("odour", "Foul Odor & Decomposing Garbage"),
    ("stench", "Foul Odor & Decomposing Garbage"),
    ("chemical", "Hazardous Chemical / Toxic Waste"),
    ("hazard", "Hazardous Chemical / Toxic Waste"),
    ("toxic", "Hazardous Chemical / Toxic Waste"),
    ("hospital", "Medical & Biohazard Waste"),
    ("medical", "Medical & Biohazard Waste"),
    ("syringe", "Medical & Biohazard Waste"),
    ("electronic", "E-Waste & Broken Electronics"),
    ("wire", "E-Waste & Broken Electronics"),
    ("furniture", "Bulk Furniture & Old Mattresses"),
    ("mattress", "Bulk Furniture & Old Mattresses"),
    ("tree", "Tree Branches & Garden Waste"),
    ("branch", "Tree Branches & Garden Waste"),
    ("leaf", "Scattered Dry Leaves / Biomass"),
    ("leaves", "Scattered Dry Leaves / Biomass"),
    ("animal", "Animal Waste & Carcass"),
    ("dump", "Illegal Open Dumping Site"),
    ("glass", "Broken Glass & Sharp Metal"),
    ("metal", "Industrial Scrap Material"),
    ("vegetable", "Market & Vegetable Waste"),
    ("fruit", "Market & Vegetable Waste"),
    ("food", "Food Waste & Kitchen Leftovers"),
    ("pothole", "Damaged Pavement / Road Hazard"),
    ("manhole", "Open Manhole & Broken Cover"),
    ("park", "Public Park & Playground Litter"),
    ("playground", "Public Park & Playground Litter"),
    ("child", "Public Park & Playground Litter"),
    ("pipe", "Water Pipe Leakage"),
    ("leak", "Water Pipe Leakage"),
    ("tyre", "Discarded Tyres & Rubber"),
    ("tire", "Discarded Tyres & Rubber"),
]


class ClassificationResult:
    """Outcome of a classification attempt."""

    __slots__ = ("category", "tags", "source", "confidence", "reasoning")

    def __init__(
        self,
        category: ComplaintCategory,
        tags: list[str] | None = None,
        source: str = "heuristic",
        confidence: float | None = None,
        reasoning: str | None = None,
    ) -> None:
        self.category = category
        self.tags = tags or ["Roadside Street Litter", "Overflowing Garbage Bin", "Plastic Waste & Bottles"]
        self.source = source
        self.confidence = confidence
        self.reasoning = reasoning


class ComplaintClassificationService:
    @staticmethod
    def classify(
        db: Session,
        complaint: Complaint,
        *,
        image_bytes: bytes | None = None,
        image_mime: str = "image/jpeg",
    ) -> ClassificationResult:
        """Classify ``complaint``, assign 3 tags, and persist results."""
        result = ComplaintClassificationService._classify_with_claude(
            complaint, image_bytes=image_bytes, image_mime=image_mime
        )
        if result is None:
            result = ComplaintClassificationService._classify_with_heuristic(complaint)

        update_payload: dict[str, object] = {
            "category": result.category.value,
            "tags": json.dumps(result.tags),
        }
        ComplaintRepository.update(db, complaint, update_payload)
        return result

    @staticmethod
    def _read_complaint_image(complaint: Complaint) -> tuple[bytes, str] | None:
        """Try to load image bytes from complaint photo_url or uploads path."""
        if not complaint.photo_url:
            return None
        url = complaint.photo_url
        if url.startswith("data:"):
            try:
                header, b64 = url.split(",", 1)
                ctype = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
                return base64.b64decode(b64), ctype
            except Exception:
                return None
        try:
            filename = Path(url).name
            upload_path = settings.upload_dir / filename
            if upload_path.exists() and upload_path.is_file():
                content = upload_path.read_bytes()
                ext = upload_path.suffix.lower()
                mime = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
                return content, mime
        except Exception:
            return None
        return None

    @staticmethod
    def _classify_with_claude(
        complaint: Complaint,
        *,
        image_bytes: bytes | None = None,
        image_mime: str = "image/jpeg",
    ) -> ClassificationResult | None:
        if not settings.anthropic_api_key:
            return None

        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic package not installed; using heuristic classification.")
            return None

        img_data = (image_bytes, image_mime) if image_bytes else ComplaintClassificationService._read_complaint_image(complaint)
        allowed = [category.value for category in ComplaintCategory]

        try:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            user_content: list[dict[str, object]] = []

            if img_data and img_data[0]:
                raw_bytes, mime = img_data
                b64_img = base64.b64encode(raw_bytes).decode("utf-8")
                user_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": b64_img,
                        },
                    }
                )

            user_content.append(
                {
                    "type": "text",
                    "text": (
                        f"Complaint description: {complaint.description}\n"
                        f"Location: {complaint.address or 'unknown'}\n"
                        f"Candidate tags list: {json.dumps(PREDEFINED_TAGS)}\n"
                        "Classify the hazard category and select the top 3 best-fitting tags from the list."
                    ),
                }
            )

            response = client.messages.create(
                model=_CLAUDE_MODEL,
                max_tokens=256,
                system=(
                    "You are a civic municipal waste classifier. Choose the single best hazard category "
                    "from the fixed set and select exactly 3 most relevant tags from the candidate list."
                ),
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string", "enum": allowed},
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string", "enum": PREDEFINED_TAGS},
                                    "minItems": 3,
                                    "maxItems": 3,
                                },
                                "confidence": {"type": "number"},
                            },
                            "required": ["category", "tags", "confidence"],
                            "additionalProperties": False,
                        },
                    },
                },
                messages=[{"role": "user", "content": user_content}],
            )
        except Exception:  # noqa: BLE001
            logger.exception("Claude classification request failed; using heuristic fallback.")
            return None

        if response.stop_reason == "refusal":
            logger.warning("Claude declined the classification request; using heuristic fallback.")
            return None

        text = next((block.text for block in response.content if block.type == "text"), "")
        try:
            data = json.loads(text)
            category = ComplaintCategory(data["category"])
            tags = [t for t in data.get("tags", []) if t in PREDEFINED_TAGS][:3]
            if len(tags) < 3:
                tags = ComplaintClassificationService._fallback_tags(complaint)
            confidence = float(data.get("confidence", 0.9))
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Claude returned an unparseable classification %r; using heuristic.", text)
            return None

        return ClassificationResult(category=category, tags=tags, source="llm", confidence=confidence)

    @staticmethod
    def _fallback_tags(complaint: Complaint) -> list[str]:
        haystack = f"{complaint.title or ''} {complaint.description or ''} {complaint.address or ''}".lower()
        matched: list[str] = []
        for keyword, tag in _KEYWORD_TAG_RULES:
            if keyword in haystack and tag not in matched:
                matched.append(tag)
                if len(matched) == 3:
                    break

        # If less than 3, pad with default diverse tags
        defaults = [
            "Roadside Street Litter",
            "Overflowing Garbage Bin",
            "Plastic Waste & Bottles",
            "Clogged Drain / Sewer Overflow",
            "Foul Odor & Decomposing Garbage",
        ]
        for d in defaults:
            if d not in matched:
                matched.append(d)
            if len(matched) == 3:
                break
        return matched[:3]

    @staticmethod
    def _classify_with_heuristic(complaint: Complaint) -> ClassificationResult:
        haystack = f"{complaint.description or ''} {complaint.address or ''}".lower()
        cat = ComplaintCategory.NONE
        reason = "no hazard keywords matched"
        for keyword, category in _KEYWORD_RULES:
            if keyword in haystack:
                cat = category
                reason = f"matched keyword '{keyword}'"
                break

        tags = ComplaintClassificationService._fallback_tags(complaint)
        return ClassificationResult(
            category=cat,
            tags=tags,
            source="heuristic",
            reasoning=reason,
        )
