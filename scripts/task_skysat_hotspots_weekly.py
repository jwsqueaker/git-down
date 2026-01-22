#!/usr/bin/env python3
"""
Create SkySat tasking orders for hotspot polygons.
Submits weekly tasking requests for high-priority areas.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from planet import Auth, Session, OrdersClient
import geopandas as gpd


def load_hotspots(hotspots_dir: str) -> List[Dict[str, Any]]:
    """
    Load all hotspot GeoJSONs from a directory.

    Args:
        hotspots_dir: Directory containing hotspot GeoJSON files

    Returns:
        List of hotspot features with metadata
    """
    hotspots = []
    hotspot_files = list(Path(hotspots_dir).glob("*.geojson"))

    for geojson_file in hotspot_files:
        gdf = gpd.read_file(geojson_file)

        # Convert to WGS84 if needed
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        for idx, row in gdf.iterrows():
            hotspot = {
                "geometry": row.geometry.__geo_interface__,
                "name": geojson_file.stem,
                "properties": dict(row.drop("geometry")),
            }
            hotspots.append(hotspot)

    return hotspots


def create_skysat_tasking_order(
    hotspot: Dict[str, Any],
    start_time: str,
    end_time: str,
    cloud_threshold: float = 0.1,
    off_nadir_angle_max: float = 20.0,
    acquisitions: int = 1,
) -> Dict[str, Any]:
    """
    Create a SkySat tasking order configuration.

    Args:
        hotspot: Hotspot dict with geometry
        start_time: Start time (ISO 8601)
        end_time: End time (ISO 8601)
        cloud_threshold: Max cloud cover fraction
        off_nadir_angle_max: Max off-nadir angle in degrees
        acquisitions: Number of acquisitions requested

    Returns:
        Order configuration dict
    """
    geometry = hotspot["geometry"]
    name = hotspot.get("name", "hotspot")

    order = {
        "name": f"SkySat_Tasking_{name}_{start_time}",
        "products": [
            {
                "item_ids": [],  # Empty for tasking
                "item_type": "SkySatCollect",
                "product_bundle": "analytic_udm2",
            }
        ],
        "metadata": {
            "start_time": start_time,
            "end_time": end_time,
            "geometry": geometry,
            "cloud_threshold": cloud_threshold,
            "off_nadir_angle_max": off_nadir_angle_max,
            "acquisitions": acquisitions,
        },
        "tools": [
            {
                "clip": {
                    "aoi": geometry,
                }
            }
        ],
    }

    return order


def submit_tasking_order(
    client: OrdersClient,
    order: Dict[str, Any],
    dry_run: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Submit a tasking order to Planet.

    Args:
        client: OrdersClient instance
        order: Order configuration dict
        dry_run: If True, print order but don't submit

    Returns:
        Response dict if submitted, None if dry run
    """
    if dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN - Would submit the following order:")
        print(json.dumps(order, indent=2))
        print("=" * 80)
        return None

    try:
        response = client.create_order(order)
        return response
    except Exception as e:
        print(f"Error submitting order: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create SkySat tasking orders for hotspot areas"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("PL_API_KEY"),
        help="Planet API key (or set PL_API_KEY env var)",
    )
    parser.add_argument(
        "--hotspots-dir",
        default="data/hotspots",
        help="Directory containing hotspot GeoJSON files",
    )
    parser.add_argument(
        "--start-time",
        help="Start time for tasking window (ISO 8601, default: now)",
    )
    parser.add_argument(
        "--end-time",
        help="End time for tasking window (ISO 8601, default: +7 days)",
    )
    parser.add_argument(
        "--cloud-threshold",
        type=float,
        default=0.1,
        help="Maximum cloud cover fraction (0.0-1.0)",
    )
    parser.add_argument(
        "--off-nadir-angle-max",
        type=float,
        default=20.0,
        help="Maximum off-nadir angle in degrees",
    )
    parser.add_argument(
        "--acquisitions",
        type=int,
        default=1,
        help="Number of acquisitions requested",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print orders without submitting",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: Planet API key required. Set PL_API_KEY env var or use --api-key", file=sys.stderr)
        sys.exit(1)

    # Set time window
    if args.start_time:
        start_time = args.start_time
    else:
        start_time = datetime.utcnow().isoformat() + "Z"

    if args.end_time:
        end_time = args.end_time
    else:
        end_dt = datetime.utcnow() + timedelta(days=7)
        end_time = end_dt.isoformat() + "Z"

    print(f"Tasking window: {start_time} to {end_time}")

    # Load hotspots
    print(f"\nLoading hotspots from {args.hotspots_dir}...")

    if not os.path.exists(args.hotspots_dir):
        print(f"Error: Hotspots directory not found: {args.hotspots_dir}", file=sys.stderr)
        sys.exit(1)

    hotspots = load_hotspots(args.hotspots_dir)

    if not hotspots:
        print("No hotspots found")
        sys.exit(0)

    print(f"Found {len(hotspots)} hotspot(s)")

    # Create client
    if not args.dry_run:
        print("\nConnecting to Planet API...")
        auth = Auth.from_key(args.api_key)
        session = Session(auth=auth)
        client = OrdersClient(session)
    else:
        client = None

    # Submit orders
    submitted = []

    for hotspot in hotspots:
        name = hotspot.get("name", "unknown")
        print(f"\nProcessing hotspot: {name}")

        # Create order
        order = create_skysat_tasking_order(
            hotspot,
            start_time=start_time,
            end_time=end_time,
            cloud_threshold=args.cloud_threshold,
            off_nadir_angle_max=args.off_nadir_angle_max,
            acquisitions=args.acquisitions,
        )

        # Submit
        response = submit_tasking_order(client, order, dry_run=args.dry_run)

        if response:
            order_id = response.get("id", "unknown")
            state = response.get("state", "unknown")

            print(f"  Order ID: {order_id}")
            print(f"  State: {state}")

            submitted.append({
                "hotspot": name,
                "order_id": order_id,
                "state": state,
            })

    # Summary
    if not args.dry_run:
        print(f"\n{'=' * 80}")
        print(f"Submitted {len(submitted)} tasking order(s)")

        for item in submitted:
            print(f"  {item['hotspot']}: {item['order_id']} ({item['state']})")
    else:
        print(f"\nDRY RUN: Would have submitted {len(hotspots)} order(s)")


if __name__ == "__main__":
    main()
