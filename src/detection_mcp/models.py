"""Public input models and domain enums."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ImageStatus(StrEnum):
    UNANNOTATED = "unannotated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AnnotationType(StrEnum):
    BBOX = "bbox"
    ROTATED_BBOX = "rotated_bbox"


class ExportMode(StrEnum):
    AUTOTRAIN = "autotrain"
    EXTENDED = "extended"


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class BBoxCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int = Field(gt=0)
    bbox: list[float] = Field(min_length=4, max_length=4)


class RotatedBBoxCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int = Field(gt=0)
    polygon: list[float] = Field(min_length=8, max_length=8)
