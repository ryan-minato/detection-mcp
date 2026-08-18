"""Public input models and domain enums."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ImageStatus(StrEnum):
    """Annotation workflow states assignable to an image."""

    UNANNOTATED = "unannotated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AnnotationType(StrEnum):
    """Geometry types stored by the annotation service."""

    BBOX = "bbox"
    ROTATED_BBOX = "rotated_bbox"


class ExportMode(StrEnum):
    """Supported metadata export layouts."""

    AUTOTRAIN = "autotrain"
    EXTENDED = "extended"


class CategoryCreate(BaseModel):
    """Validate one category creation request.

    Attributes:
        name: Non-empty category name, unique among active dataset categories.
        description: Optional authoritative description for annotators.

    Notes:
        Unknown fields are rejected and surrounding name whitespace is removed.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class BBoxCreate(BaseModel):
    """Validate the shape of one axis-aligned annotation request.

    Attributes:
        category_id: Positive identifier of an active category.
        bbox: Four normalized coordinates in ``[x1, y1, x2, y2]`` order.

    Notes:
        Coordinate ordering and range are enforced by the geometry service.
    """

    model_config = ConfigDict(extra="forbid")

    category_id: int = Field(gt=0)
    bbox: list[float] = Field(min_length=4, max_length=4)


class RotatedBBoxCreate(BaseModel):
    """Validate the shape of one rotated annotation request.

    Attributes:
        category_id: Positive identifier of an active category.
        polygon: Four normalized vertices flattened as eight coordinates.

    Notes:
        Convexity, ordering, and rectangularity are enforced by the geometry
        service.
    """

    model_config = ConfigDict(extra="forbid")

    category_id: int = Field(gt=0)
    polygon: list[float] = Field(min_length=8, max_length=8)
