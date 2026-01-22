#!/usr/bin/env python3
"""
List all available Planet Basemap series for your account.
"""

import os
import sys
import argparse
from planet import Auth, Session
from planet.clients.basemaps import BasemapsClient


def list_basemap_series(api_key: str):
    """
    List all basemap series available to the account.

    Args:
        api_key: Planet API key
    """
    print("Fetching basemap series...")
    print("-" * 80)

    try:
        # Create authenticated session
        auth = Auth.from_key(api_key)
        session = Session(auth=auth)
        client = BasemapsClient(session)

        # List series
        series_list = client.list_series()

        # Display results
        count = 0
        for series in series_list:
            series_id = series.get("id", "N/A")
            series_name = series.get("name", "N/A")
            series_type = series.get("item_type", "N/A")
            created = series.get("created", "N/A")

            print(f"ID:      {series_id}")
            print(f"Name:    {series_name}")
            print(f"Type:    {series_type}")
            print(f"Created: {created}")
            print("-" * 80)

            count += 1

        print(f"\nTotal series found: {count}")

        if count == 0:
            print("\nNo basemap series found for this account.")
            print("You may need to subscribe to a basemap series via the Planet Explorer.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="List all Planet Basemap series available to your account"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("PL_API_KEY"),
        help="Planet API key (or set PL_API_KEY env var)",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: Planet API key required. Set PL_API_KEY env var or use --api-key", file=sys.stderr)
        sys.exit(1)

    list_basemap_series(args.api_key)


if __name__ == "__main__":
    main()
