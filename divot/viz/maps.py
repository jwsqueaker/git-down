"""Folium map helpers for IRI heat-maps and pothole markers."""

from __future__ import annotations

from typing import Sequence

import folium
from folium.plugins import HeatMap

from divot.detect.detector import Detection
from divot.iri.quarter_car import IRISegment


def _iri_color(iri: float) -> str:
    """Return a colour string based on IRI severity."""
    if iri < 2.0:
        return "green"
    if iri < 4.0:
        return "orange"
    return "red"


def iri_heatmap(
    segments: Sequence[IRISegment],
    zoom_start: int = 13,
) -> folium.Map:
    """Create a Folium map with IRI colour-coded segments."""
    if not segments:
        return folium.Map(location=[0, 0], zoom_start=2)

    center_lat = sum(s.start_lat for s in segments) / len(segments)
    center_lon = sum(s.start_lon for s in segments) / len(segments)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start)

    for seg in segments:
        folium.PolyLine(
            locations=[(seg.start_lat, seg.start_lon), (seg.end_lat, seg.end_lon)],
            color=_iri_color(seg.iri),
            weight=5,
            tooltip=f"IRI: {seg.iri:.2f} m/km",
        ).add_to(m)

    # Overlay heat-map
    heat_data = [
        [(s.start_lat + s.end_lat) / 2, (s.start_lon + s.end_lon) / 2, s.iri]
        for s in segments
    ]
    HeatMap(heat_data, radius=20).add_to(m)
    return m


def pothole_map(
    detections: Sequence[tuple[float, float, Detection]],
    zoom_start: int = 15,
) -> folium.Map:
    """Map pothole detections.  Each item is ``(lat, lon, Detection)``."""
    if not detections:
        return folium.Map(location=[0, 0], zoom_start=2)

    center_lat = sum(d[0] for d in detections) / len(detections)
    center_lon = sum(d[1] for d in detections) / len(detections)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start)

    for lat, lon, det in detections:
        folium.CircleMarker(
            location=[lat, lon],
            radius=max(4, det.area / 500),
            color="red",
            fill=True,
            popup=f"Confidence: {det.confidence:.2f}",
        ).add_to(m)

    return m
