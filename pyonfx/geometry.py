from __future__ import annotations
import math
from typing import Sequence
import numpy as np
from dataclasses import dataclass
from shapely.geometry import Polygon
from shapely import affinity
from shapely.algorithms.cga import signed_area as shapely_signed_area

Point = tuple[float, float]


def centroid(points: list[Point]) -> Point:
    """
    Compute the geometric centroid (arithmetic mean of vertex coordinates)
    of a closed polygon.

    Parameters:
        points (list[Point]): Vertices of the polygon in any winding order. The polygon is assumed to be *closed* – i.e. the first and last vertex are considered connected even if they are not equal.

    Returns:
        The *(x, y)* coordinates of the centroid.
    """
    centroid = Polygon(points).centroid
    return (float(centroid.x), float(centroid.y))


def signed_area(points: list[Point]) -> float:
    """
    Return the *signed* area of a polygon using the shoelace formula.

    A positive value indicates that the vertices are ordered
    counter-clockwise (CCW), while a negative value indicates a clockwise
    order.

    Parameters:
        points (list[Point]): Vertices of the polygon. The list does **not** need to repeat the first point at the end – the function automatically wraps around.

    Returns:
        The signed area of the polygon.
    """
    return shapely_signed_area(Polygon(points).exterior)


def scale_polygon(
    points: list[Point],
    scale_factor: float,
    center: Point | None = None,
) -> list[Point] | None:
    """
    Return a uniformly scaled copy of *points*.

    The polygon is scaled by ``scale_factor`` with respect to ``center``.
    If *center* is *None* the geometric centroid of *points* is used.

    Parameters:
        points (list[Point]): Vertices of the polygon to scale.
        scale_factor (float): Multiplicative scale factor. Values must be strictly greater than zero – a factor of *1.0* leaves the geometry unchanged.
        center (Point, optional): *(x, y)* coordinates of the scaling origin. Defaults to :func:`centroid` of *points* when omitted.

    Returns:
        The scaled polygon vertices, or ``None`` when the requested scale would collapse the polygon into a degenerate point.
    """
    if scale_factor <= 0 or len(points) < 3:
        return None

    poly = Polygon(points)
    if not poly.is_valid or poly.area == 0:
        return None

    if center is None:
        c = poly.centroid
        cx, cy = c.x, c.y
    else:
        cx, cy = center

    scaled = affinity.scale(
        poly, xfact=scale_factor, yfact=scale_factor, origin=(cx, cy)
    )

    if scaled.is_empty or scaled.area == 0:
        return None

    # Exclude closing vertex
    coords = list(scaled.exterior.coords[:-1])
    return coords


def mean_distance_from_origin(points: list[Point]) -> float:
    """
    Compute the mean Euclidean distance of *points* from the origin.

    This helper is primarily used as a quick-and-dirty *scale estimate* when
    normalising shapes that live in different coordinate spaces.

    Parameters:
        points (list[Point]): Arbitrary collection of points.

    Returns:
        The average distance.  When *points* is empty the function returns ``1.0`` to avoid a division-by-zero error.
    """
    if not points:
        return 1.0

    arr = np.array(points)
    return np.mean(np.linalg.norm(arr, axis=1))


def find_preserved_perimeter_positions(
    points: list[Point],
    distances: list[float],
    preserve_points: list[Point],
) -> list[float]:
    """
    Convert a list of *arbitrary* points to their position on the perimeter
    of ``points`` expressed as *cumulative distance*.

    The function is primarily used to guarantee that certain vertices - for
    example sharp corners - survive a subsequent call to
    :func:`resample_perimeter_points`.

    Parameters:
        points (list[Point]): Source polygon vertices.
        distances (list[float]): Cumulative perimeter distances for each entry in *points*. The array must therefore have the same length as *points*.
        preserve_points (list[Point]): Points that should be *preserved* exactly during resampling.

    Returns:
        The cumulative-distance position of each preserved point along the polygon perimeter.
    """
    if not preserve_points:
        return []

    pts = np.asarray(points, dtype=float)
    preserve = np.asarray(preserve_points, dtype=float)
    dists = np.asarray(distances, dtype=float)

    # Segment vectors and their squared lengths
    seg_vec = pts[1:] - pts[:-1]
    seg_len_sq = np.sum(seg_vec**2, axis=1)

    preserved = []
    for p in preserve:
        # Vector from p1 to preserve point for every segment start
        dp = p - pts[:-1]
        # Projection parameter t for each segment (0..1 clamped)
        proj = np.divide(
            np.sum(dp * seg_vec, axis=1),
            seg_len_sq,
            where=seg_len_sq != 0,
            out=np.zeros_like(seg_len_sq, dtype=float),
        )
        t = np.clip(proj, 0.0, 1.0)

        # Closest points and squared distances for all segments at once
        closest = pts[:-1] + seg_vec * t[:, None]
        dist_sq = np.sum((p - closest) ** 2, axis=1)

        best_idx = int(dist_sq.argmin())
        best_distance = dists[best_idx] + t[best_idx] * (
            dists[best_idx + 1] - dists[best_idx]
        )
        preserved.append(float(best_distance))

    return preserved


def perimeter_distances_to_points(
    points: list[Point],
    distances: list[float],
    targets: list[float],
    target_count: int,
) -> list[Point]:
    """
    Convert a list of *cumulative perimeter distances* back into *(x, y)*
    coordinates on the polygon.

    Parameters:
        points (list[Point]): Original polygon vertices.
        distances (list[float]): Cumulative perimeter distances for *points*.
        targets (list[float]): Perimeter distances that should be mapped back to coordinates.
        target_count (int): Length of the coordinate list that should be returned. When *targets* is shorter than this value the last computed coordinate is repeated until the desired length is reached.

    Returns:
        Interpolated coordinates.
    """
    # Convert inputs to NumPy arrays for vectorised operations
    pts = np.asarray(points, dtype=float)
    dists = np.asarray(distances, dtype=float)
    targets_arr = np.asarray(targets, dtype=float)

    # Map each target distance to its segment index using searchsorted
    seg_idx = np.searchsorted(dists, targets_arr, side="right") - 1
    seg_idx = np.clip(seg_idx, 0, len(dists) - 2)

    seg_start = dists[seg_idx]
    seg_end = dists[seg_idx + 1]
    seg_len = seg_end - seg_start

    t_seg = np.divide(
        targets_arr - seg_start,
        seg_len,
        where=seg_len != 0,
        out=np.zeros_like(targets_arr, dtype=float),
    )

    p1 = pts[seg_idx]
    p2 = pts[seg_idx + 1]
    coords_arr = p1 + (p2 - p1) * t_seg[:, None]

    # Ensure length == target_count (pad/re-slice as before)
    if coords_arr.shape[0] < target_count:
        pad_count = target_count - coords_arr.shape[0]
        pad_vals = (
            np.tile(coords_arr[-1], (pad_count, 1))
            if coords_arr.size
            else np.tile(pts[-1], (pad_count, 1))
        )
        coords_arr = np.vstack([coords_arr, pad_vals])

    return [tuple(p) for p in coords_arr[:target_count]]


def resample_perimeter_points(
    points: list[Point],
    target_count: int,
    preserve_points: list[Point] | None = None,
) -> list[Point]:
    """
    Resample the vertices of a polygon so that its perimeter is represented
    by exactly ``target_count`` points.

    The algorithm distributes new points *uniformly* along the perimeter
    but, when requested, keeps specific vertices intact (see
    ``preserve_points``).

    Parameters:
        points (list[Point]): Vertices of the polygon to be resampled.
        target_count (int): Desired number of output points.
        preserve_points (list[Point], optional): Vertices that must appear unchanged in the output. If *None* (the default) no points are preserved.

    Returns:
        A new list containing exactly *target_count* points.
    """
    if not points:
        raise ValueError("Cannot resample an empty point list")
    if len(points) == 1:
        return [points[0]] * target_count

    pts = np.asarray(points, dtype=float)

    # Cumulative perimeter distances
    dxy = np.diff(pts, axis=0)
    distances_arr = np.insert(np.cumsum(np.linalg.norm(dxy, axis=1)), 0, 0.0)
    total = float(distances_arr[-1])

    if total == 0.0:
        return [points[0]] * target_count

    preserved = (
        find_preserved_perimeter_positions(
            points, distances_arr.tolist(), preserve_points
        )
        if preserve_points
        else []
    )

    target_ds: set[float] = set(preserved)
    needed = target_count - len(preserved)
    if needed > 0:
        # Uniformly spaced distances along the perimeter.
        target_ds.update((i / max(1, needed - 1)) * total for i in range(needed))

    sorted_ds = np.sort(np.fromiter(target_ds, dtype=float))[:target_count]
    return perimeter_distances_to_points(
        points, distances_arr.tolist(), sorted_ds.tolist(), target_count
    )


# ------------------------  Alignment helpers  ---------------------------


def find_best_alignment(
    normalized_source: list[Point],
    centered_target: list[Point],
) -> tuple[int, list[Point]]:
    """
    Find the rotation and winding direction of *centered_target* that minimises
    the *per-vertex* distance to *normalized_source*.

    The search is brute-force but fast enough for the typical point counts we
    deal with (hundreds at most).

    Parameters:
        normalized_source (list[Point]): Source polygon that has already been normalised (centred & scaled).
        centered_target (list[Point]): Target polygon that is centred, but *not* necessarily scaled or oriented like *normalized_source*.

    Returns:
        The offset into *centered_target* that yields the best alignment as well as the (possibly reversed) list that achieved that alignment.
    """
    # Convert source to a NumPy array for efficient vector maths.
    src = np.asarray(normalized_source, dtype=float)

    best_offset: int = 0
    best_cost: float = float("inf")
    best_variant: list[Point] = centered_target

    # Evaluate both possible windings: original and reversed.
    for variant in (centered_target, list(reversed(centered_target))):
        tgt = np.asarray(variant, dtype=float)
        if len(src) != len(tgt):
            # Fallback to the slow but safe original behaviour.
            tgt_list = variant  # keep alias for clarity
            for off in range(len(tgt_list)):
                cost = sum(
                    math.hypot(
                        src[i][0] - tgt_list[(i + off) % len(tgt_list)][0],
                        src[i][1] - tgt_list[(i + off) % len(tgt_list)][1],
                    )
                    for i in range(len(src))
                )
                if cost < best_cost:
                    best_cost = cost
                    best_offset = off
                    best_variant = variant
            continue

        n = len(tgt)
        # Evaluate offsets in chunks of ~5 % of the perimeter to reduce work.
        step = max(1, n // 20)
        for off in range(0, n, step):
            rolled = np.roll(tgt, -off, axis=0)
            cost = float(np.linalg.norm(src - rolled, axis=1).sum())
            if cost < best_cost:
                best_cost = cost
                best_offset = off
                best_variant = variant

    return best_offset, best_variant


def apply_alignment(
    target_points: list[Point],
    best_target_list: list[Point],
    best_offset: int,
    centered_target: list[Point],
) -> list[Point]:
    """Re-order *target_points* according to the chosen alignment settings."""
    pts = np.asarray(target_points, dtype=float)
    is_same_orientation = best_target_list is centered_target
    if not is_same_orientation:
        pts = pts[::-1]

    rolled = np.roll(pts, -best_offset, axis=0)
    return [tuple(p) for p in rolled]


@dataclass(slots=True)
class Compound:
    shell: list[Point]
    holes: list[list[Point]]

    def centroid(self) -> Point:
        return centroid(self.shell)

    def signed_area(self) -> float:
        return signed_area(self.shell)


def _pair_compounds_by_centroid(
    src_compounds: Sequence[Compound],
    tgt_compounds: Sequence[Compound],
) -> list[tuple[Compound | None, Compound | None]]:
    """Greedy nearest-centroid matching (original behaviour)."""

    paired: list[tuple[Compound | None, Compound | None]] = []

    src_centroids = [c.centroid() for c in src_compounds]
    tgt_centroids = [c.centroid() for c in tgt_compounds]

    src_unused = list(range(len(src_compounds)))
    tgt_unused = list(range(len(tgt_compounds)))

    while src_unused and tgt_unused:
        best_si = best_ti = None  # type: ignore
        best_dist = float("inf")
        for si in src_unused:
            sx, sy = src_centroids[si]
            for ti in tgt_unused:
                tx, ty = tgt_centroids[ti]
                dist = (sx - tx) * (sx - tx) + (sy - ty) * (sy - ty)
                if dist < best_dist:
                    best_dist = dist
                    best_si, best_ti = si, ti
        assert best_si is not None and best_ti is not None
        paired.append((src_compounds[best_si], tgt_compounds[best_ti]))
        src_unused.remove(best_si)
        tgt_unused.remove(best_ti)

    for si in src_unused:
        paired.append((src_compounds[si], None))
    for ti in tgt_unused:
        paired.append((None, tgt_compounds[ti]))

    return paired


def _pair_compounds_by_order(
    src_compounds: Sequence[Compound],
    tgt_compounds: Sequence[Compound],
) -> list[tuple[Compound | None, Compound | None]]:
    """Match compounds strictly by left-to-right order (centroid X)."""

    src_sorted = sorted(src_compounds, key=lambda c: c.centroid()[0])
    tgt_sorted = sorted(tgt_compounds, key=lambda c: c.centroid()[0])

    paired: list[tuple[Compound | None, Compound | None]] = []
    m = min(len(src_sorted), len(tgt_sorted))
    for i in range(m):
        paired.append((src_sorted[i], tgt_sorted[i]))
    for i in range(m, len(src_sorted)):
        paired.append((src_sorted[i], None))
    for i in range(m, len(tgt_sorted)):
        paired.append((None, tgt_sorted[i]))
    return paired


def pair_compounds(
    src_compounds: Sequence[Compound],
    tgt_compounds: Sequence[Compound],
) -> list[tuple[Compound | None, Compound | None]]:
    """Heuristically pair two *compound* lists (glyph outlines).

    Two strategies are tried:

    1. *Centroid-greedy*  (minimise point distance)
    2. *Left-to-right*    (keep reading order along the X axis)

    The cheaper assignment according to a simple Δx² cost wins.
    """

    if not src_compounds and not tgt_compounds:
        return []

    pairs_cent = _pair_compounds_by_centroid(src_compounds, tgt_compounds)
    pairs_order = _pair_compounds_by_order(src_compounds, tgt_compounds)

    def assignment_cost(pairs):
        total = 0.0
        for s, t in pairs:
            if s is None or t is None:
                # Penalise appear / disappear heavily so existing glyphs
                # prefer real matches.
                total += 1e6
                continue
            (sx, _sy) = s.centroid()
            (tx, _ty) = t.centroid()
            total += (sx - tx) * (sx - tx)  # horizontal cost only
        return total

    cost_cent = assignment_cost(pairs_cent)
    cost_ord = assignment_cost(pairs_order)

    return pairs_order if cost_ord < cost_cent else pairs_cent


def deduplicate_loops(loops: list[list[Point]]) -> list[list[Point]]:
    """Remove *exact duplicates* in *loops* (rounded to 3 decimals)."""
    unique_serialized = set()
    deduped: list[list[Point]] = []
    for lp in loops:
        key = tuple((round(x, 3), round(y, 3)) for x, y in lp)
        if key not in unique_serialized:
            unique_serialized.add(key)
            deduped.append(lp)
    return deduped
