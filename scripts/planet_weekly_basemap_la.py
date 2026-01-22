#!/usr/bin/env python3
"""
Fetch weekly Planet Basemap imagery for Los Angeles City.
Downloads the latest mosaic from a specified series.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from planet import Auth, Session
from planet.clients.basemaps import BasemapsClient
import geopandas as gpd
from tqdm import tqdm
import requests


def load_aoi(aoi_path: str) -> tuple:
    """
    Load AOI and return geometry and bounds.

    Returns:
        Tuple of (geometry, bbox)
    """
    gdf = gpd.read_file(aoi_path)

    # Get first geometry (assume single feature or use union)
    if len(gdf) > 1:
        geom = gdf.unary_union
    else:
        geom = gdf.geometry.iloc[0]

    # Get bounding box
    bbox = gdf.total_bounds  # [minx, miny, maxx, maxy]

    return geom, bbox


def find_series_by_name(client: BasemapsClient, series_name: str) -> Optional[Dict[str, Any]]:
    """
    Find a basemap series by exact name match.

    Args:
        client: BasemapsClient instance
        series_name: Exact series name to find

    Returns:
        Series dict if found, None otherwise
    """
    series_list = client.list_series()

    for series in series_list:
        if series.get("name") == series_name:
            return series

    return None


def get_latest_mosaic(client: BasemapsClient, series_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest mosaic from a series.

    Args:
        client: BasemapsClient instance
        series_id: Series ID

    Returns:
        Latest mosaic dict
    """
    mosaics = list(client.list_mosaics(series_id))

    if not mosaics:
        return None

    # Sort by last_acquired or created date
    mosaics.sort(
        key=lambda m: m.get("last_acquired") or m.get("created"),
        reverse=True,
    )

    return mosaics[0]


def get_quads_for_bbox(
    client: BasemapsClient,
    mosaic_id: str,
    bbox: tuple,
) -> List[Dict[str, Any]]:
    """
    Get quads intersecting a bounding box.

    Args:
        client: BasemapsClient instance
        mosaic_id: Mosaic ID
        bbox: Bounding box (minx, miny, maxx, maxy)

    Returns:
        List of quad dicts
    """
    minx, miny, maxx, maxy = bbox

    # Convert to bbox string format for Planet API
    bbox_str = f"{minx},{miny},{maxx},{maxy}"

    try:
        quads = list(client.list_quads(mosaic_id, bbox=bbox_str))
        return quads
    except Exception as e:
        print(f"Warning: bbox search failed: {e}")
        print("Fetching all quads and filtering...")

        # Fallback: get all quads and filter
        all_quads = list(client.list_quads(mosaic_id))
        filtered = []

        for quad in all_quads:
            quad_bbox = quad.get("bbox")
            if quad_bbox:
                qminx, qminy, qmaxx, qmaxy = quad_bbox
                # Check intersection
                if not (qmaxx < minx or qminx > maxx or qmaxy < miny or qminy > maxy):
                    filtered.append(quad)

        return filtered


def download_quad(quad: Dict[str, Any], output_dir: Path, api_key: str) -> bool:
    """
    Download a single quad as GeoTIFF.

    Args:
        quad: Quad dict with download links
        output_dir: Directory to save to
        api_key: Planet API key for authentication

    Returns:
        True if successful
    """
    quad_id = quad.get("id", "unknown")
    download_url = quad.get("_links", {}).get("download")

    if not download_url:
        print(f"Warning: No download link for quad {quad_id}")
        return False

    output_file = output_dir / f"{quad_id}.tif"

    # Skip if already exists
    if output_file.exists():
        print(f"Skipping {quad_id} (already exists)")
        return True

    try:
        # Download with authentication
        response = requests.get(
            download_url,
            auth=(api_key, ""),
            stream=True,
        )
        response.raise_for_status()

        # Get total size
        total_size = int(response.headers.get("content-length", 0))

        # Download with progress bar
        with open(output_file, "wb") as f:
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=quad_id,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        return True

    except Exception as e:
        print(f"Error downloading {quad_id}: {e}")
        if output_file.exists():
            output_file.unlink()
        return False


def build_vrt(output_dir: Path, mosaic_date: str):
    """
    Build a VRT from downloaded quads.

    Args:
        output_dir: Directory containing quads
        mosaic_date: Date string for VRT filename
    """
    import subprocess

    tif_files = list(output_dir.glob("*.tif"))

    if not tif_files:
        print("No TIF files found to build VRT")
        return

    vrt_path = output_dir.parent / f"la_weekly_{mosaic_date}.vrt"

    # Build VRT using gdalbuildvrt
    cmd = ["gdalbuildvrt", str(vrt_path)] + [str(f) for f in tif_files]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Created VRT: {vrt_path}")

        # Create symlink to latest
        latest_vrt = output_dir.parent / "la_weekly_latest.vrt"
        if latest_vrt.exists():
            latest_vrt.unlink()
        latest_vrt.symlink_to(vrt_path.name)

    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not build VRT: {e}")
    except Exception as e:
        print(f"Warning: Could not create VRT symlink: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch weekly Planet Basemap for Los Angeles"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("PL_API_KEY"),
        help="Planet API key (or set PL_API_KEY env var)",
    )
    parser.add_argument(
        "--series-name",
        default=os.getenv("PL_SERIES_NAME"),
        required=True,
        help="Exact name of the basemap series (or set PL_SERIES_NAME env var)",
    )
    parser.add_argument(
        "--aoi",
        default="data/la_city_boundary.geojson",
        help="Path to LA City boundary GeoJSON",
    )
    parser.add_argument(
        "--output-dir",
        default="data/weekly_la_basemap",
        help="Directory to save downloaded imagery",
    )
    parser.add_argument(
        "--delivery",
        choices=["local", "s3"],
        default="local",
        help="Delivery method (local download or S3)",
    )
    parser.add_argument(
        "--aws-bucket",
        default=os.getenv("AWS_BUCKET"),
        help="S3 bucket for delivery (if delivery=s3)",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: Planet API key required. Set PL_API_KEY env var or use --api-key", file=sys.stderr)
        sys.exit(1)

    if args.delivery == "s3":
        print("Error: S3 delivery not yet implemented. Use delivery=local", file=sys.stderr)
        sys.exit(1)

    # Load AOI
    print(f"Loading AOI from {args.aoi}...")
    if not os.path.exists(args.aoi):
        print(f"Error: AOI file not found: {args.aoi}", file=sys.stderr)
        print("Please download LA City boundary from LA Open Data Portal", file=sys.stderr)
        sys.exit(1)

    geom, bbox = load_aoi(args.aoi)
    print(f"AOI bbox: {bbox}")

    # Create client
    print("Connecting to Planet API...")
    auth = Auth.from_key(args.api_key)
    session = Session(auth=auth)
    client = BasemapsClient(session)

    # Find series
    print(f"Finding series: {args.series_name}")
    series = find_series_by_name(client, args.series_name)

    if not series:
        print(f"Error: Series '{args.series_name}' not found", file=sys.stderr)
        print("Run planet_list_series.py to see available series", file=sys.stderr)
        sys.exit(1)

    series_id = series["id"]
    print(f"Found series: {series_id}")

    # Get latest mosaic
    print("Finding latest mosaic...")
    mosaic = get_latest_mosaic(client, series_id)

    if not mosaic:
        print("Error: No mosaics found in series", file=sys.stderr)
        sys.exit(1)

    mosaic_id = mosaic["id"]
    mosaic_name = mosaic.get("name", mosaic_id)
    mosaic_date = mosaic.get("last_acquired", mosaic.get("created", "unknown"))

    print(f"Latest mosaic: {mosaic_name}")
    print(f"Date: {mosaic_date}")

    # Get quads
    print("Finding quads intersecting AOI...")
    quads = get_quads_for_bbox(client, mosaic_id, bbox)

    print(f"Found {len(quads)} quads")

    if not quads:
        print("Warning: No quads found for AOI")
        sys.exit(0)

    # Create output directory
    date_str = mosaic_date.split("T")[0] if "T" in mosaic_date else mosaic_date
    output_dir = Path(args.output_dir) / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading to {output_dir}")

    # Download quads
    success_count = 0
    for quad in quads:
        if download_quad(quad, output_dir, args.api_key):
            success_count += 1

    print(f"\nDownloaded {success_count}/{len(quads)} quads")

    # Build VRT
    if success_count > 0:
        print("\nBuilding VRT...")
        build_vrt(output_dir, date_str)

        # Create symlink to latest
        latest_dir = Path(args.output_dir) / "latest"
        if latest_dir.exists():
            latest_dir.unlink()
        try:
            latest_dir.symlink_to(date_str)
            print(f"Created symlink: {latest_dir} -> {date_str}")
        except Exception as e:
            print(f"Warning: Could not create directory symlink: {e}")

        print("\nDone! Use the VRT file for processing.")


if __name__ == "__main__":
    main()
