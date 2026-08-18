"""Public input models and domain enums."""

from enum import StrEnum
from typing import Literal

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


class _PublicModel(BaseModel):
    """Reject undeclared fields at the MCP output boundary."""

    model_config = ConfigDict(extra="forbid")


class DatasetRecord(_PublicModel):
    """Describe one dataset through the stable public interface."""

    dataset_id: int
    name: str | None
    root_path: str
    deleted_at: str | None
    created_at: str
    updated_at: str


class DatasetList(_PublicModel):
    """Contain ordered dataset records and their count."""

    datasets: list[DatasetRecord]
    count: int


class CategoryRecord(_PublicModel):
    """Describe one category through the stable public interface."""

    category_id: int
    dataset_id: int
    name: str
    description: str | None
    deleted_at: str | None
    created_at: str
    updated_at: str


class CategoryList(_PublicModel):
    """Contain ordered category records and their count."""

    categories: list[CategoryRecord]
    count: int


class ImageRecord(_PublicModel):
    """Describe a discovered image and its annotation workflow status."""

    image_path: str
    status: ImageStatus


class ImageList(_PublicModel):
    """Contain one page of discovered images and stable paging metadata."""

    images: list[ImageRecord]
    total: int
    offset: int
    count: int
    random_seed: int


class ImageStatusRecord(_PublicModel):
    """Describe the stored workflow status for one dataset image."""

    dataset_id: int
    image_path: str
    status: ImageStatus
    updated_at: str


class AnnotationRecord(_PublicModel):
    """Describe one stored annotation through the stable public interface."""

    annotation_id: int
    dataset_id: int
    image_path: str
    type: AnnotationType
    category_id: int
    geometry: list[float]
    created_at: str
    updated_at: str


class ListedAnnotationRecord(AnnotationRecord):
    """Add category metadata needed when listing or rendering annotations."""

    category_name: str
    category_deleted_at: str | None


class RotatedAnnotationRecord(AnnotationRecord):
    """Include correction diagnostics returned for a rotated annotation write."""

    submitted_geometry: list[float]
    stored_geometry: list[float]
    corrected: bool
    deviation: float
    warning: str | None


class AnnotationList(_PublicModel):
    """Contain one page of annotation records and stable paging metadata."""

    annotations: list[ListedAnnotationRecord]
    total: int
    offset: int
    count: int


class AnnotationBatch(_PublicModel):
    """Contain created axis-aligned annotations and their count."""

    annotations: list[AnnotationRecord]
    count: int


class RotatedAnnotationBatch(_PublicModel):
    """Contain created rotated annotations and their correction diagnostics."""

    annotations: list[RotatedAnnotationRecord]
    count: int


class DeletedAnnotations(_PublicModel):
    """Report annotation identifiers removed by one atomic delete operation."""

    deleted_annotation_ids: list[int]
    count: int


class PreviewMetadata(_PublicModel):
    """Describe an orientation-corrected image preview."""

    original_width: int
    original_height: int
    preview_width: int
    preview_height: int
    scale: float
    orientation_applied: bool
    dataset_id: int
    image_path: str
    clamped: bool


class AnnotationPreviewMetadata(PreviewMetadata):
    """Add the number of annotations rendered into an overlay preview."""

    annotation_count: int


class ExportRecord(_PublicModel):
    """Report the result of a completed metadata export."""

    output_path: str
    export_mode: ExportMode
    exported_images: int
    category_mapping: dict[str, int]
    ignored_rotated_annotations: int
    excluded_deleted_category_annotations: int


class SuccessEnvelope[DataT](_PublicModel):
    """Wrap one typed successful MCP result."""

    ok: Literal[True] = True
    data: DataT
