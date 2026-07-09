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


# Approximate geographic centroid for every African country. Locations are
# country-level now; the city coords above are kept for backward compatibility.
COUNTRY_COORDS = {
    "Algeria": (28.03, 1.66), "Angola": (-11.20, 17.87), "Benin": (9.31, 2.32),
    "Botswana": (-22.33, 24.68), "Burkina Faso": (12.24, -1.56),
    "Burundi": (-3.37, 29.92), "Cabo Verde": (16.00, -24.01),
    "Cameroon": (7.37, 12.35), "Central African Republic": (6.61, 20.94),
    "Chad": (15.45, 18.73), "Comoros": (-11.65, 43.33), "Congo (DRC)": (-4.04, 21.76),
    "Congo (Republic)": (-0.23, 15.83), "Cote d'Ivoire": (7.54, -5.55),
    "Djibouti": (11.83, 42.59), "Egypt": (26.82, 30.80),
    "Equatorial Guinea": (1.65, 10.27), "Eritrea": (15.18, 39.78),
    "Eswatini": (-26.52, 31.47), "Ethiopia": (9.15, 40.49), "Gabon": (-0.80, 11.61),
    "Gambia": (13.44, -15.31), "Ghana": (7.95, -1.02), "Guinea": (9.95, -9.70),
    "Guinea-Bissau": (11.80, -15.18), "Kenya": (-0.02, 37.91),
    "Lesotho": (-29.61, 28.23), "Liberia": (6.43, -9.43), "Libya": (26.34, 17.23),
    "Madagascar": (-18.77, 46.87), "Malawi": (-13.25, 34.30), "Mali": (17.57, -4.00),
    "Mauritania": (21.01, -10.94), "Mauritius": (-20.35, 57.55),
    "Morocco": (31.79, -7.09), "Mozambique": (-18.67, 35.53),
    "Namibia": (-22.96, 18.49), "Niger": (17.61, 8.08), "Nigeria": (9.08, 8.68),
    "Rwanda": (-1.94, 29.87), "Sao Tome and Principe": (0.19, 6.61),
    "Senegal": (14.50, -14.45), "Seychelles": (-4.68, 55.49),
    "Sierra Leone": (8.46, -11.78), "Somalia": (5.15, 46.20),
    "South Africa": (-30.56, 22.94), "South Sudan": (6.88, 31.31),
    "Sudan": (12.86, 30.22), "Tanzania": (-6.37, 34.89), "Togo": (8.62, 0.82),
    "Tunisia": (33.89, 9.54), "Uganda": (1.37, 32.29), "Zambia": (-13.13, 27.85),
    "Zimbabwe": (-19.02, 29.15),
}


def coords_for_region(region):
    """Coordinates for a location. Countries first; legacy cities as fallback."""
    if region in COUNTRY_COORDS:
        return COUNTRY_COORDS[region]
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
