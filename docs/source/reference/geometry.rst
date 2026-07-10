.. _geometry-ref:

Geometry Helpers
================

The geometry helpers normalize polygonal Shapely results and centralize the
repair fallbacks needed by vector-heavy effects. They accept ``Polygon``,
``MultiPolygon``, and polygonal members of ``GeometryCollection`` objects and
return ``MultiPolygon`` consistently.

Typical use
-----------

Use an explicit bounds check when disjoint geometry is common, then call the
robust operation::

   from pyonfx import bounds_intersect, safe_intersection

   if bounds_intersect(shape.bounds, mask.bounds):
       clipped = safe_intersection(shape, mask)

The bounds guard is intentionally separate. For geometry that usually
overlaps, calling the direct boolean helper avoids adding an unnecessary
check. ``safe_difference`` also provides an opt-in ``shrink_fallback``; this
is not enabled by default because shrinking the inner geometry changes the
mathematical result.

``repair_geometry`` is best effort. Invalid inputs are repaired through
Shapely/GEOS fallbacks, while empty or non-polygonal inputs become an empty
``MultiPolygon``. Applications that require exact topology should still
validate area and component invariants for their own fixtures.

API reference
-------------

.. automodule:: pyonfx.geometry
   :members:
