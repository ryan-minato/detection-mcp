import math

import pytest

from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.services.geometry import validate_bbox, validate_rotated_bbox

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "bbox",
    ([0.0, 0.0, 1.0, 1.0], [0.1, 0.2, 0.8, 0.9]),
)
def test_validate_bbox_accepts_normalized_xyxy(bbox: list[float]) -> None:
    assert validate_bbox(bbox) == bbox


@pytest.mark.parametrize(
    "bbox",
    (
        [0.5, 0.0, 0.5, 1.0],
        [-0.1, 0.0, 1.0, 1.0],
        [0.0, 0.0, 1.1, 1.0],
        [0.0, math.nan, 1.0, 1.0],
        [0.0, 0.0, math.inf, 1.0],
        [0.0, 0.0, 1.0],
    ),
)
def test_validate_bbox_rejects_invalid_values(bbox: list[float]) -> None:
    with pytest.raises(DomainError) as captured:
        validate_bbox(bbox)
    assert captured.value.code is ErrorCode.INVALID_BBOX


def test_rotated_bbox_canonicalizes_exact_rectangle() -> None:
    result = validate_rotated_bbox(
        [0.8, 0.8, 0.2, 0.8, 0.2, 0.2, 0.8, 0.2],
        correction_enabled=True,
        correction_threshold=0.01,
        error_threshold=0.05,
    )
    assert result.corrected is False
    assert result.stored_geometry == pytest.approx([0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8])


def test_rotated_bbox_corrects_small_deviation() -> None:
    result = validate_rotated_bbox(
        [0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.795],
        correction_enabled=True,
        correction_threshold=0.01,
        error_threshold=0.05,
    )
    assert result.corrected is True
    assert result.warning is None
    assert result.deviation < 0.01


@pytest.mark.parametrize(
    "polygon",
    (
        [0.2, 0.2, 0.8, 0.8, 0.8, 0.2, 0.2, 0.8],
        [0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.8, 0.8],
        [0.2, 0.2, 0.8, 0.2, 0.5, 0.2, 0.2, 0.8],
    ),
)
def test_rotated_bbox_rejects_invalid_topology(polygon: list[float]) -> None:
    with pytest.raises(DomainError) as captured:
        validate_rotated_bbox(
            polygon,
            correction_enabled=True,
            correction_threshold=0.01,
            error_threshold=0.05,
        )
    assert captured.value.code is ErrorCode.INVALID_ROTATED_BBOX


def test_rotated_bbox_rejects_large_correction() -> None:
    with pytest.raises(DomainError) as captured:
        validate_rotated_bbox(
            [0.1, 0.1, 0.9, 0.1, 0.7, 0.9, 0.3, 0.9],
            correction_enabled=True,
            correction_threshold=0.01,
            error_threshold=0.05,
        )
    assert captured.value.code is ErrorCode.ROTATED_BBOX_CORRECTION_EXCEEDED
