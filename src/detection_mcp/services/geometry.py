"""Bounding-box validation and rotated rectangle correction."""

import math
from dataclasses import dataclass

from detection_mcp.errors import DomainError, ErrorCode

Point = tuple[float, float]
EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class RotatedGeometry:
    """Describe submitted and persisted rotated-box geometry.

    Attributes:
        submitted_geometry: Coordinates exactly as supplied by the caller.
        stored_geometry: Canonical coordinates persisted by the service.
        corrected: Whether rectangle fitting changed the geometry.
        deviation: Maximum normalized vertex displacement from the fitted box.
        warning: Optional warning when correction exceeds the warning threshold.
    """

    submitted_geometry: list[float]
    stored_geometry: list[float]
    corrected: bool
    deviation: float
    warning: str | None = None


def validate_bbox(values: list[float], *, field: str = "bbox") -> list[float]:
    """Validate and normalize an axis-aligned bounding box.

    Args:
        values: Coordinates in normalized ``[x1, y1, x2, y2]`` order.
        field: Input field name used in structured errors.

    Returns:
        A new list containing finite float coordinates.

    Raises:
        DomainError: If the box has the wrong shape, order, or range.
    """
    if len(values) != 4 or not all(math.isfinite(value) for value in values):
        raise DomainError(ErrorCode.INVALID_BBOX, "bbox requires four finite values", field=field)
    x1, y1, x2, y2 = values
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise DomainError(
            ErrorCode.INVALID_BBOX,
            "bbox requires 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1",
            field=field,
            details={"received": values},
        )
    return [float(value) for value in values]


def _cross(a: Point, b: Point, c: Point) -> float:
    """Return the signed turn across three consecutive points."""
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])


def _orientation(a: Point, b: Point, c: Point) -> float:
    """Return the signed orientation of three points."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    """Check whether two segments cross strictly inside their spans."""
    return (
        _orientation(a, b, c) * _orientation(a, b, d) < -EPSILON
        and _orientation(c, d, a) * _orientation(c, d, b) < -EPSILON
    )


def _signed_area(points: list[Point]) -> float:
    """Return the signed area of a four-point polygon."""
    return (
        sum(
            points[index][0] * points[(index + 1) % 4][1] - points[(index + 1) % 4][0] * points[index][1]
            for index in range(4)
        )
        / 2
    )


def _canonical(points: list[Point]) -> list[Point]:
    """Order vertices consistently and start at the top-left point."""
    ordered = points if _signed_area(points) > 0 else list(reversed(points))
    start = min(range(4), key=lambda index: (ordered[index][1], ordered[index][0]))
    return ordered[start:] + ordered[:start]


def _flatten(points: list[Point]) -> list[float]:
    """Flatten point pairs into the public polygon representation."""
    return [coordinate for point in points for coordinate in point]


def _fit_rectangle(points: list[Point]) -> tuple[list[Point], float]:
    """Fit the closest oriented rectangle over candidate edge angles."""
    submitted = _canonical(points)
    best: tuple[list[Point], float] | None = None
    for index in range(4):
        start, end = points[index], points[(index + 1) % 4]
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        cosine, sine = math.cos(angle), math.sin(angle)
        rotated = [(x * cosine + y * sine, -x * sine + y * cosine) for x, y in points]
        minimum_x = min(point[0] for point in rotated)
        maximum_x = max(point[0] for point in rotated)
        minimum_y = min(point[1] for point in rotated)
        maximum_y = max(point[1] for point in rotated)
        corners = [
            (minimum_x, minimum_y),
            (maximum_x, minimum_y),
            (maximum_x, maximum_y),
            (minimum_x, maximum_y),
        ]
        fitted = _canonical([(x * cosine - y * sine, x * sine + y * cosine) for x, y in corners])
        distances = [math.dist(submitted[item], fitted[item]) for item in range(4)]
        diagonal = math.dist(fitted[0], fitted[2])
        deviation = max(distances) / diagonal if diagonal > EPSILON else math.inf
        if best is None or deviation < best[1]:
            best = (fitted, deviation)
    if best is None:
        raise RuntimeError("rectangle fitting requires four points")
    return best


def validate_rotated_bbox(
    values: list[float],
    *,
    correction_enabled: bool,
    correction_threshold: float,
    error_threshold: float,
    field: str = "polygon",
) -> RotatedGeometry:
    """Validate, canonicalize, and optionally correct a rotated box.

    Args:
        values: Four normalized polygon vertices flattened as eight values.
        correction_enabled: Whether a non-rectangular quadrilateral may be fit.
        correction_threshold: Deviation above which a warning is returned.
        error_threshold: Deviation above which correction is rejected.
        field: Input field name used in structured errors.

    Returns:
        Submitted and canonical stored geometry with correction metadata.

    Raises:
        DomainError: If the polygon is invalid or needs excessive correction.

    Notes:
        Vertex order is canonicalized even when no geometric correction is
        required. Source image coordinates remain normalized to ``[0, 1]``.
    """
    # Reject malformed, out-of-bounds, repeated, crossing, or concave input.
    if len(values) != 8 or not all(math.isfinite(value) for value in values):
        raise DomainError(
            ErrorCode.INVALID_ROTATED_BBOX,
            "rotated bbox requires eight finite values",
            field=field,
        )
    if not all(0 <= value <= 1 for value in values):
        raise DomainError(
            ErrorCode.INVALID_ROTATED_BBOX,
            "rotated bbox coordinates must be in [0, 1]",
            field=field,
        )
    points = [(float(values[index]), float(values[index + 1])) for index in range(0, 8, 2)]
    if len(set(points)) != 4:
        raise DomainError(ErrorCode.INVALID_ROTATED_BBOX, "rotated bbox vertices must be unique", field=field)
    if _segments_intersect(points[0], points[1], points[2], points[3]) or _segments_intersect(
        points[1], points[2], points[3], points[0]
    ):
        raise DomainError(ErrorCode.INVALID_ROTATED_BBOX, "rotated bbox must not self-intersect", field=field)
    crosses = [_cross(points[index], points[(index + 1) % 4], points[(index + 2) % 4]) for index in range(4)]
    if any(abs(value) <= EPSILON for value in crosses) or not (
        all(value > 0 for value in crosses) or all(value < 0 for value in crosses)
    ):
        raise DomainError(ErrorCode.INVALID_ROTATED_BBOX, "rotated bbox must be a convex quadrilateral", field=field)

    # Fit the closest rectangle and keep correction inside normalized bounds.
    fitted, deviation = _fit_rectangle(points)
    if any(coordinate < -EPSILON or coordinate > 1 + EPSILON for point in fitted for coordinate in point):
        raise DomainError(
            ErrorCode.INVALID_ROTATED_BBOX,
            "corrected rotated bbox would leave the normalized image bounds",
            field=field,
        )
    fitted = [(min(1.0, max(0.0, x)), min(1.0, max(0.0, y))) for x, y in fitted]
    canonical_submitted = _canonical(points)
    # Select exact, rejected, or corrected output from configured thresholds.
    if deviation <= EPSILON:
        return RotatedGeometry(list(values), _flatten(canonical_submitted), False, deviation)
    if not correction_enabled:
        raise DomainError(ErrorCode.INVALID_ROTATED_BBOX, "rotated bbox is not rectangular", field=field)
    if deviation > error_threshold:
        raise DomainError(
            ErrorCode.ROTATED_BBOX_CORRECTION_EXCEEDED,
            "rotated bbox correction exceeds the configured error threshold",
            field=field,
            details={"deviation": deviation, "error_threshold": error_threshold},
        )
    warning = None
    if deviation > correction_threshold:
        warning = "rotated bbox was corrected beyond the warning threshold"
    return RotatedGeometry(list(values), _flatten(fitted), True, deviation, warning)
