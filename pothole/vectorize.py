"""
Vectorization utilities to convert raster predictions to polygons.
"""

import numpy as np
from typing import List, Dict, Any, Optional
import rasterio
from rasterio import features
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import geopandas as gpd
from scipy import ndimage
import cv2


def raster_to_polygons(
    mask: np.ndarray,
    transform: Any,
    crs: Any,
    probability_map: Optional[np.ndarray] = None,
    min_area: float = 1.0,
    simplify_tolerance: float = 0.5,
    morphological_cleanup: bool = True,
    kernel_size: int = 3,
) -> List[Dict[str, Any]]:
    """
    Convert a binary mask to georeferenced polygon features.

    Args:
        mask: Binary mask array (H, W) with 1 for pothole, 0 for background
        transform: Rasterio affine transform
        crs: Coordinate reference system
        probability_map: Optional probability map for confidence calculation
        min_area: Minimum area threshold (in CRS units squared)
        simplify_tolerance: Tolerance for geometry simplification
        morphological_cleanup: Apply morphological opening/closing
        kernel_size: Kernel size for morphological operations

    Returns:
        List of GeoJSON features
    """
    # Ensure binary
    mask = (mask > 0).astype(np.uint8)

    # Morphological cleanup to reduce noise
    if morphological_cleanup:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        # Opening: removes small objects
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        # Closing: fills small holes
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Extract polygons using rasterio
    shapes_gen = features.shapes(
        mask.astype(np.int16),
        mask=(mask > 0),
        transform=transform,
    )

    features_list = []

    for geom, value in shapes_gen:
        if value == 0:  # Skip background
            continue

        # Create shapely geometry
        poly = shape(geom)

        # Filter by area
        if poly.area < min_area:
            continue

        # Simplify geometry
        if simplify_tolerance > 0:
            poly = poly.simplify(simplify_tolerance, preserve_topology=True)

        # Calculate confidence if probability map provided
        confidence = None
        if probability_map is not None:
            # Get mask for this polygon
            poly_mask = features.rasterize(
                [(mapping(poly), 1)],
                out_shape=mask.shape,
                transform=transform,
                fill=0,
                dtype=np.uint8,
            )
            # Calculate mean probability
            poly_pixels = probability_map[poly_mask > 0]
            if len(poly_pixels) > 0:
                confidence = float(np.mean(poly_pixels))

        # Build feature
        feature = {
            "type": "Feature",
            "geometry": mapping(poly),
            "properties": {
                "area_crs_units": float(poly.area),
            },
        }

        if confidence is not None:
            feature["properties"]["confidence"] = confidence

        features_list.append(feature)

    return features_list


def polygons_to_geojson(
    polygons: List[Dict[str, Any]],
    crs: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a GeoJSON FeatureCollection from polygon features.

    Args:
        polygons: List of GeoJSON features
        crs: Coordinate reference system
        metadata: Optional metadata to add to properties

    Returns:
        GeoJSON FeatureCollection dict
    """
    # Add metadata to each feature if provided
    if metadata:
        for poly in polygons:
            poly["properties"].update(metadata)

    geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": str(crs)},
        },
        "features": polygons,
    }

    return geojson


def add_area_m2(geojson: Dict[str, Any], crs: Any) -> Dict[str, Any]:
    """
    Add area_m2 field to features in a GeoJSON.

    Args:
        geojson: GeoJSON FeatureCollection
        crs: Source CRS

    Returns:
        Updated GeoJSON with area_m2 field
    """
    from .geo import calculate_area_m2

    for feature in geojson["features"]:
        geom = shape(feature["geometry"])
        area_m2 = calculate_area_m2(geom, crs)

        if area_m2 is not None:
            feature["properties"]["area_m2"] = float(area_m2)

    return geojson


def filter_polygons(
    geojson: Dict[str, Any],
    min_area_m2: Optional[float] = None,
    min_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Filter polygons by area and confidence.

    Args:
        geojson: GeoJSON FeatureCollection
        min_area_m2: Minimum area in square meters
        min_confidence: Minimum confidence score

    Returns:
        Filtered GeoJSON
    """
    filtered_features = []

    for feature in geojson["features"]:
        props = feature["properties"]

        # Check area
        if min_area_m2 is not None:
            area = props.get("area_m2")
            if area is None or area < min_area_m2:
                continue

        # Check confidence
        if min_confidence is not None:
            confidence = props.get("confidence")
            if confidence is None or confidence < min_confidence:
                continue

        filtered_features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": filtered_features,
    }


def merge_nearby_polygons(
    geojson: Dict[str, Any],
    buffer_distance: float = 2.0,
) -> Dict[str, Any]:
    """
    Merge polygons that are close to each other.

    Args:
        geojson: GeoJSON FeatureCollection
        buffer_distance: Distance to buffer for merging

    Returns:
        GeoJSON with merged polygons
    """
    if not geojson["features"]:
        return geojson

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])

    # Buffer, union, and unbuffer
    buffered = gdf.geometry.buffer(buffer_distance)
    merged = unary_union(buffered)
    unbuffered = merged.buffer(-buffer_distance)

    # Convert back to GeoJSON
    if unbuffered.geom_type == "Polygon":
        geometries = [unbuffered]
    elif unbuffered.geom_type == "MultiPolygon":
        geometries = list(unbuffered.geoms)
    else:
        geometries = []

    features = []
    for geom in geometries:
        features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {},
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
