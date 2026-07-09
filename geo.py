"""
geo.py
-------
Approximate coordinates for FarmConnect's regions, and a straight-line
distance calculator (the haversine formula) so the market page can show
buyers which farmers are closest to them.

This is region-to-region distance (city center to city center), not
precise GPS - there's no per-user exact location stored in this app.
"""

import math

# Approximate latitude/longitude for each of FarmConnect's current regions.
REGION_COORDS = {
    "Nairobi": (-1.2921, 36.8219),
    "Kano": (12.0022, 8.5920),
    "Lagos": (6.5244, 3.3792),
    "Kumasi": (6.6885, -1.6244),
    "Kampala": (0.3476, 32.5825),
    "Arusha": (-3.3869, 36.6830),
    "Addis Ababa": (9.0320, 38.7469),
    "Dakar": (14.7167, -17.4677),
    "Cairo": (30.0444, 31.2357),
    "Casablanca": (33.5731, -7.5898),
    "Tunis": (36.8065, 10.1815),
    "Johannesburg": (-26.2041, 28.0473),
    "Harare": (-17.8252, 31.0335),
    "Lusaka": (-15.3875, 28.3228),
    "Kigali": (-1.9441, 30.0619),
    "Maputo": (-25.9692, 32.5732),
    "Kinshasa": (-4.4419, 15.2663),
    "Yaounde": (3.8480, 11.5021),
    "Luanda": (-8.8390, 13.2894),
    "Khartoum": (15.5007, 32.5599),
}


def coords_for_region(region):
    return REGION_COORDS.get(region)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometers."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def distance_between_regions(region_a, region_b):
    """Distance in km between two regions, or None if either is unknown."""
    a = coords_for_region(region_a)
    b = coords_for_region(region_b)
    if not a or not b:
        return None
    return haversine_km(a[0], a[1], b[0], b[1])
