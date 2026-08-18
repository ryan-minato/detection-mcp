# Geometry Guide

The preview and annotation tools use the orientation-corrected image coordinate
space. The top-left pixel is the origin; `x` increases to the right and `y`
increases downward.

## Axis-aligned boxes

Provide `[x_min, y_min, x_max, y_max]` normalized to the range `[0, 1]`. All
values must be finite. The minimum coordinate must be strictly smaller than the
maximum coordinate on both axes.

## Rotated boxes

Provide four distinct corner points. The server validates bounds, convexity,
non-zero area, and edge intersections, then normalizes the point order.

The server may replace a nearly rectangular quadrilateral with a fitted rotating
rectangle. Deviation is the largest corner displacement divided by the fitted
rectangle diagonal. A deviation above 1% produces an explicit warning, and a
deviation above 5% is rejected.

Always call `preview_annotations` after adding or editing rotated geometry.
