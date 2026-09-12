from __future__ import annotations

from math import atan2, cos, degrees, radians, sin, sqrt

from atalaya.core.models import GeoAssessment, GeoPoint

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(origin: GeoPoint, target: GeoPoint) -> int:
    lat1 = radians(origin.lat)
    lat2 = radians(target.lat)
    delta_lat = radians(target.lat - origin.lat)
    delta_lon = radians(target.lon - origin.lon)

    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(EARTH_RADIUS_M * c)


def bearing_degrees(origin: GeoPoint, target: GeoPoint) -> int:
    lat1 = radians(origin.lat)
    lat2 = radians(target.lat)
    delta_lon = radians(target.lon - origin.lon)

    y = sin(delta_lon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(delta_lon)
    bearing = (degrees(atan2(y, x)) + 360) % 360
    return round(bearing)


def bearing_to_cardinal_es(bearing: int) -> str:
    directions = [
        "norte",
        "noreste",
        "este",
        "sureste",
        "sur",
        "suroeste",
        "oeste",
        "noroeste",
    ]
    index = round((bearing % 360) / 45) % 8
    return directions[index]


def assess_relative_position(origin: GeoPoint, target: GeoPoint) -> GeoAssessment:
    bearing = bearing_degrees(origin, target)
    return GeoAssessment(
        distance_m=haversine_distance_m(origin, target),
        bearing_deg=bearing,
        relative_direction=bearing_to_cardinal_es(bearing),
    )
