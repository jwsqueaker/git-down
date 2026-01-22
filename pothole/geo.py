"""
Geospatial utilities for coordinate transformations and area calculations.
"""

import json
from typing import Dict, Any, Optional
import geopandas as gpd
from shapely.geometry import shape, mapping
from pyproj import CRS, Transformer
import numpy as np


def reproject_geojson(
    geojson_data: Dict[str, Any],
    source_crs: str,
    target_crs: str = "EPSG:4326",
) -> Dict[str, Any]:
    """
    Reproject a GeoJSON from source CRS to target CRS.

    Args:
        geojson_data: GeoJSON dict or FeatureCollection
        source_crs: Source CRS (e.g., 'EPSG:32611')
        target_crs: Target CRS (default WGS84)

    Returns:
        Reprojected GeoJSON dict
    """
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"], crs=source_crs)
    gdf = gdf.to_crs(target_crs)

    # Rebuild GeoJSON
    output = {
        "type": "FeatureCollection",
        "features": json.loads(gdf.to_json())["features"],
    }

    return output


def get_crs_area_multiplier(crs: Any) -> Optional[float]:
    """
    Get the multiplier to convert CRS units to square meters.

    Args:
        crs: Rasterio CRS object or EPSG code

    Returns:
        Multiplier for area calculation, or None if CRS is geographic
    """
    try:
        crs_obj = CRS.from_user_input(crs)

        # Check if projected (has linear units)
        if crs_obj.is_projected:
            # Get axis info
            axis = crs_obj.axis_info[0]
            unit_name = axis.unit_name.lower()

            # Convert to square meters
            if "meter" in unit_name or "metre" in unit_name:
                return 1.0
            elif "foot" in unit_name or "feet" in unit_name:
                return 0.09290304  # square feet to square meters
            elif "kilometre" in unit_name or "kilometer" in unit_name:
                return 1_000_000.0  # square km to square meters
            else:
                # Unknown unit, return 1.0 and warn
                print(f"Warning: Unknown unit {unit_name}, assuming meters")
                return 1.0
        else:
            # Geographic CRS (lat/lon) - no direct area calculation
            return None

    except Exception as e:
        print(f"Warning: Could not determine CRS units: {e}")
        return None


def calculate_area_m2(geometry, crs: Any) -> Optional[float]:
    """
    Calculate area of a geometry in square meters.

    Args:
        geometry: Shapely geometry
        crs: CRS of the geometry

    Returns:
        Area in square meters, or None if calculation fails
    """
    multiplier = get_crs_area_multiplier(crs)

    if multiplier is None:
        # For geographic CRS, reproject to appropriate UTM zone
        # Get centroid
        centroid = geometry.centroid
        lon, lat = centroid.x, centroid.y

        # Determine UTM zone
        utm_zone = int((lon + 180) / 6) + 1
        hemisphere = "north" if lat >= 0 else "south"
        utm_crs = f"+proj=utm +zone={utm_zone} +{hemisphere} +datum=WGS84 +units=m +no_defs"

        # Reproject
        try:
            source_crs = CRS.from_user_input(crs)
            target_crs = CRS.from_proj4(utm_crs)
            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

            # Transform geometry
            from shapely.ops import transform
            projected_geom = transform(transformer.transform, geometry)
            return projected_geom.area
        except Exception as e:
            print(f"Warning: Could not reproject for area calculation: {e}")
            return None
    else:
        return geometry.area * multiplier


def load_aoi(geojson_path: str) -> gpd.GeoDataFrame:
    """
    Load an Area of Interest from a GeoJSON file.

    Args:
        geojson_path: Path to GeoJSON file

    Returns:
        GeoDataFrame with AOI geometry
    """
    gdf = gpd.read_file(geojson_path)
    return gdf


def clip_raster_to_aoi(raster_path: str, aoi_path: str, output_path: str) -> None:
    """
    Clip a raster to an AOI boundary.

    Args:
        raster_path: Path to input raster
        aoi_path: Path to AOI GeoJSON
        output_path: Path for output clipped raster
    """
    import rasterio
    from rasterio.mask import mask

    aoi = gpd.read_file(aoi_path)

    with rasterio.open(raster_path) as src:
        # Reproject AOI to raster CRS if needed
        if aoi.crs != src.crs:
            aoi = aoi.to_crs(src.crs)

        # Clip
        out_image, out_transform = mask(src, aoi.geometry, crop=True)
        out_meta = src.meta.copy()

        # Update metadata
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        })

        # Write clipped raster
        with rasterio.open(output_path, "w", **out_meta) as dst:
            dst.write(out_image)

    print(f"Clipped raster saved to {output_path}")


def bbox_from_geojson(geojson_path: str) -> tuple:
    """
    Extract bounding box from a GeoJSON.

    Args:
        geojson_path: Path to GeoJSON file

    Returns:
        Tuple of (minx, miny, maxx, maxy)
    """
    gdf = gpd.read_file(geojson_path)
    return gdf.total_bounds
