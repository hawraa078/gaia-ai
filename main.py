from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
import os
import json
import math
import html
import re
from functools import lru_cache
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import rasterio

load_dotenv()

app = FastAPI(
    title="GAIA API",
    description="AI Environmental Intervention Engine",
    version="0.7.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://gaia-ai-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "project": "GAIA",
        "message": "Don't just predict Earth's future. Optimize it. 🌍"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================
# HELPERS
# =========================

def valid_values(series):
    return [
        value
        for value in series.values()
        if value is not None and value > -900
    ]


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def risk_level(score):
    if score >= 80:
        return "severe"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "moderate"
    elif score >= 20:
        return "low"
    return "minimal"




# =========================
# ESA WORLDCOVER / ECOSYSTEM INTELLIGENCE
# =========================

WORLD_COVER_CLASSES = {
    10: {"land_cover": "Tree cover", "ecosystem_interpretation": "woodland_or_tree_dominated_landscape"},
    20: {"land_cover": "Shrubland", "ecosystem_interpretation": "shrubland"},
    30: {"land_cover": "Grassland", "ecosystem_interpretation": "grassland"},
    40: {"land_cover": "Cropland", "ecosystem_interpretation": "agricultural_landscape"},
    50: {"land_cover": "Built-up", "ecosystem_interpretation": "urban_or_built_up_landscape"},
    60: {"land_cover": "Bare / sparse vegetation", "ecosystem_interpretation": "arid_or_sparsely_vegetated_landscape"},
    70: {"land_cover": "Snow and ice", "ecosystem_interpretation": "snow_or_ice_dominated_landscape"},
    80: {"land_cover": "Permanent water bodies", "ecosystem_interpretation": "aquatic_landscape"},
    90: {"land_cover": "Herbaceous wetland", "ecosystem_interpretation": "wetland"},
    95: {"land_cover": "Mangroves", "ecosystem_interpretation": "mangrove_wetland"},
    100: {"land_cover": "Moss and lichen", "ecosystem_interpretation": "moss_or_lichen_dominated_landscape"},
}


def _worldcover_tile_id(lat: float, lon: float) -> str:
    if not (-90 <= lat < 90 and -180 <= lon < 180):
        raise ValueError("Coordinates are outside the ESA WorldCover tile range")

    tile_lat = math.floor(lat / 3.0) * 3
    tile_lon = math.floor(lon / 3.0) * 3

    lat_prefix = "N" if tile_lat >= 0 else "S"
    lon_prefix = "E" if tile_lon >= 0 else "W"
    return f"{lat_prefix}{abs(tile_lat):02d}{lon_prefix}{abs(tile_lon):03d}"


def _worldcover_url(tile_id: str) -> str:
    filename = f"ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"
    return (
        "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
        f"v200/2021/map/{filename}"
    )


@lru_cache(maxsize=256)
def _fetch_worldcover_cached(lat_rounded: float, lon_rounded: float):
    tile_id = _worldcover_tile_id(lat_rounded, lon_rounded)
    url = _worldcover_url(tile_id)

    # WorldCover is distributed as Cloud Optimized GeoTIFFs. GDAL/rasterio can
    # read only the small byte ranges needed for this point instead of
    # downloading the whole tile.
    env_options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_TIMEOUT": "25",
        "GDAL_HTTP_CONNECTTIMEOUT": "10",
    }

    with rasterio.Env(**env_options):
        with rasterio.open(f"/vsicurl/{url}") as src:
            sampled = next(src.sample([(lon_rounded, lat_rounded)]))
            class_code = int(sampled[0])

    class_info = WORLD_COVER_CLASSES.get(class_code)
    if class_info is None:
        raise ValueError(f"Unknown or no-data ESA WorldCover class: {class_code}")

    return {
        "class_code": class_code,
        "land_cover": class_info["land_cover"],
        "ecosystem_interpretation": class_info["ecosystem_interpretation"],
        "tile_id": tile_id,
        "source_url": url,
    }


def fetch_worldcover_landcover(lat: float, lon: float):
    # Rounding gives stable cache keys while remaining far finer than 10 m.
    return _fetch_worldcover_cached(round(lat, 6), round(lon, 6))


def ecosystem_intervention_guidance(ecosystem: dict):
    code = ecosystem["class_code"]

    guidance = {
        10: {
            "focus": "Protect existing tree cover and restore degraded patches before adding new planting.",
            "avoid": "Replacing established tree communities with climate-suitable but ecologically unverified species.",
        },
        20: {
            "focus": "Prioritize native shrubland recovery, soil stabilization, and protection from further disturbance.",
            "avoid": "Converting shrubland into dense tree plantations without ecological justification.",
        },
        30: {
            "focus": "Prioritize grassland restoration, erosion control, and recovery of locally appropriate herbaceous vegetation.",
            "avoid": "Assuming tree planting is the default restoration strategy.",
        },
        40: {
            "focus": "Use water-smart agricultural restoration, soil recovery, agroforestry only where locally appropriate, and irrigation-efficiency measures.",
            "avoid": "Large-scale habitat conversion without considering food production and land use.",
        },
        50: {
            "focus": "Favor urban heat mitigation, shade, permeable surfaces, and water-efficient urban greening using locally appropriate species.",
            "avoid": "Treating built-up land as a natural ecosystem restoration site.",
        },
        60: {
            "focus": "Prioritize soil stabilization, erosion control, water retention, and sparse native vegetation recovery where feasible.",
            "avoid": "Dense planting or high-water-demand restoration in naturally arid or bare landscapes.",
        },
        70: {
            "focus": "Protect cryosphere conditions and minimize disturbance; vegetation planting is generally not the primary intervention.",
            "avoid": "Vegetation recommendations that ignore snow/ice dominance.",
        },
        80: {
            "focus": "Prioritize water quality, hydrology, shoreline/riparian condition, and aquatic habitat before terrestrial planting.",
            "avoid": "Recommending terrestrial planting inside permanent water pixels.",
        },
        90: {
            "focus": "Prioritize wetland hydrology, water quality, salinity, and native wetland vegetation recovery.",
            "avoid": "Tree-first restoration that could alter wetland structure or water balance.",
        },
        95: {
            "focus": "Prioritize mangrove hydrology, tidal connectivity, sediment conditions, and verified native mangrove recovery.",
            "avoid": "Introducing non-mangrove terrestrial species into mangrove habitat.",
        },
        100: {
            "focus": "Protect fragile ground-cover communities and minimize disturbance.",
            "avoid": "Tree planting without evidence that woody vegetation belongs in the local system.",
        },
    }

    return guidance.get(code, {
        "focus": "Validate local ecosystem conditions before selecting an intervention.",
        "avoid": "Treating climate suitability alone as proof of ecological appropriateness.",
    })


@app.get("/ecosystem")
def get_ecosystem(lat: float, lon: float):
    """
    GAIA Ecosystem Intelligence v0.5.

    Reads ESA WorldCover 2021 v200 at the selected coordinate. WorldCover is
    a land-cover classification and is used here as an ecosystem proxy, not
    as proof of the full ecological community.
    """
    try:
        if not (-90 <= lat < 90 and -180 <= lon < 180):
            raise HTTPException(status_code=400, detail="Invalid latitude or longitude")

        result = fetch_worldcover_landcover(lat, lon)
        guidance = ecosystem_intervention_guidance(result)

        return {
            "location": {"latitude": lat, "longitude": lon},
            "land_cover": {
                "class_code": result["class_code"],
                "class_name": result["land_cover"],
                "ecosystem_interpretation": result["ecosystem_interpretation"],
            },
            "intervention_guidance": guidance,
            "source": {
                "name": "ESA WorldCover 2021 v200",
                "resolution_m": 10,
                "tile_id": result["tile_id"],
                "data_type": "Cloud Optimized GeoTIFF (COG)",
                "url": result["source_url"],
            },
            "confidence_note": (
                "WorldCover identifies land cover at the selected pixel. GAIA uses it as an "
                "ecosystem proxy; it does not by itself prove native community composition, "
                "hydrology, salinity, habitat condition, or restoration suitability."
            ),
            "engine": "GAIA Ecosystem Intelligence v0.5",
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not retrieve ESA WorldCover land cover: {error}",
        )


# =========================
# NASA POWER DATA
# =========================

def fetch_nasa_climate(lat: float, lon: float):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    values = data["properties"]["parameter"]

    temperatures = valid_values(values["T2M"])
    maximums = valid_values(values["T2M_MAX"])
    minimums = valid_values(values["T2M_MIN"])
    rainfall = valid_values(values["PRECTOTCORR"])
    humidity = valid_values(values["RH2M"])

    if not temperatures:
        raise ValueError(
            "NASA returned no valid temperature data"
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "average_temperature": (
            sum(temperatures) / len(temperatures)
        ),
        "maximum_temperature": max(maximums),
        "minimum_temperature": min(minimums),
        "total_rainfall": sum(rainfall),
        "average_humidity": (
            sum(humidity) / len(humidity)
        )
    }


# =========================
# CLIMATE ENDPOINT
# =========================

@app.get("/climate")
def get_climate(lat: float, lon: float):

    try:
        climate = fetch_nasa_climate(
            lat=lat,
            lon=lon
        )

        return {
            "location": {
                "latitude": lat,
                "longitude": lon
            },

            "period": {
                "start": str(
                    climate["start_date"]
                ),
                "end": str(
                    climate["end_date"]
                )
            },

            "climate": {
                "average_temperature_c": round(
                    climate[
                        "average_temperature"
                    ],
                    2
                ),

                "maximum_temperature_c": round(
                    climate[
                        "maximum_temperature"
                    ],
                    2
                ),

                "minimum_temperature_c": round(
                    climate[
                        "minimum_temperature"
                    ],
                    2
                ),

                "total_rainfall_mm": round(
                    climate[
                        "total_rainfall"
                    ],
                    2
                ),

                "average_humidity_percent": round(
                    climate[
                        "average_humidity"
                    ],
                    2
                )
            },

            "source": "NASA POWER"
        }

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not retrieve NASA POWER data: "
                f"{error}"
            )
        )


# =========================
# ENVIRONMENTAL RISK ENGINE
# =========================

def calculate_environmental_risk(
    avg_temp: float,
    max_temp: float,
    rainfall: float,
    humidity: float
):

    # -------------------------
    # Heat Stress
    # -------------------------

    heat_score = (
        ((avg_temp - 25) / 20) * 60
        +
        ((max_temp - 35) / 20) * 40
    )

    heat_score = clamp(
        heat_score
    )


    # -------------------------
    # Water Stress
    # -------------------------

    rainfall_score = clamp(
        ((30 - rainfall) / 30) * 100
    )

    humidity_score = clamp(
        ((50 - humidity) / 50) * 100
    )

    water_score = (
        rainfall_score * 0.65
        +
        humidity_score * 0.35
    )

    water_score = clamp(
        water_score
    )


    # -------------------------
    # Drought Pressure
    # -------------------------

    drought_score = (
        water_score * 0.60
        +
        heat_score * 0.40
    )

    drought_score = clamp(
        drought_score
    )


    # -------------------------
    # Overall Climate Risk
    # -------------------------

    overall_score = (
        heat_score * 0.35
        +
        water_score * 0.35
        +
        drought_score * 0.30
    )

    overall_score = clamp(
        overall_score
    )


    return {
        "heat_stress": {
            "score": round(
                heat_score,
                1
            ),
            "level": risk_level(
                heat_score
            )
        },

        "water_stress": {
            "score": round(
                water_score,
                1
            ),
            "level": risk_level(
                water_score
            )
        },

        "drought_pressure": {
            "score": round(
                drought_score,
                1
            ),
            "level": risk_level(
                drought_score
            )
        },

        "overall_climate_risk": {
            "score": round(
                overall_score,
                1
            ),
            "level": risk_level(
                overall_score
            )
        }
    }


# =========================
# RISK ENDPOINT
# =========================

@app.get("/risk")
def get_risk(lat: float, lon: float):

    try:
        climate = fetch_nasa_climate(
            lat=lat,
            lon=lon
        )

        risk = calculate_environmental_risk(
            avg_temp=climate[
                "average_temperature"
            ],

            max_temp=climate[
                "maximum_temperature"
            ],

            rainfall=climate[
                "total_rainfall"
            ],

            humidity=climate[
                "average_humidity"
            ]
        )

        return {
            "location": {
                "latitude": lat,
                "longitude": lon
            },

            "period": {
                "start": str(
                    climate["start_date"]
                ),
                "end": str(
                    climate["end_date"]
                )
            },

            "environmental_risk": risk,

            "inputs": {
                "average_temperature_c": round(
                    climate[
                        "average_temperature"
                    ],
                    2
                ),

                "maximum_temperature_c": round(
                    climate[
                        "maximum_temperature"
                    ],
                    2
                ),

                "total_rainfall_mm": round(
                    climate[
                        "total_rainfall"
                    ],
                    2
                ),

                "average_humidity_percent": round(
                    climate[
                        "average_humidity"
                    ],
                    2
                )
            },

            "method": (
                "GAIA interpretable "
                "environmental risk heuristic v0.1"
            ),

            "source": "NASA POWER"
        }

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not calculate environmental risk: "
                f"{error}"
            )
        )

# =========================
# SPECIES INTELLIGENCE ENGINE v0.2
# FAO ECOCROP + NASA POWER + optional GBIF locality evidence
# =========================

SPECIES_DATA_PATH = Path(__file__).with_name("gaia_species_database.csv")
_SPECIES_DF = None


def load_species_database():
    """Load and cache the cleaned FAO ECOCROP-derived species database."""
    global _SPECIES_DF

    if _SPECIES_DF is not None:
        return _SPECIES_DF

    if not SPECIES_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Species database not found: {SPECIES_DATA_PATH}. "
            "Place gaia_species_database.csv next to main.py."
        )

    df = pd.read_csv(SPECIES_DATA_PATH)

    required_columns = {
        "scientific_name",
        "family",
        "temp_min_c",
        "temp_max_c",
        "rainfall_min_mm_year",
        "rainfall_max_mm_year",
        "ph_min",
        "ph_max",
        "uses",
        "source",
    }

    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(
            "Species database is missing required columns: "
            + ", ".join(sorted(missing))
        )

    numeric_columns = [
        "temp_min_c",
        "temp_max_c",
        "rainfall_min_mm_year",
        "rainfall_max_mm_year",
        "ph_min",
        "ph_max",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    _SPECIES_DF = df
    return _SPECIES_DF


def fetch_nasa_species_climate(lat: float, lon: float):
    """
    Fetch a trailing 365-day climate window for species matching.
    ECOCROP rainfall requirements are annual, so this is more appropriate
    than comparing them with GAIA's 30-day risk window.
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=364)

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "T2M,PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    values = data["properties"]["parameter"]

    temperatures = valid_values(values["T2M"])
    rainfall = valid_values(values["PRECTOTCORR"])

    if not temperatures or not rainfall:
        raise ValueError("NASA returned incomplete annual climate data")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "annual_mean_temperature_c": sum(temperatures) / len(temperatures),
        "annual_rainfall_mm": sum(rainfall),
    }


def range_match_score(value, minimum, maximum, outside_decay):
    """Return a 0-100 suitability score for a value against a preferred range."""
    if pd.isna(minimum) or pd.isna(maximum):
        return None

    minimum = float(minimum)
    maximum = float(maximum)

    if minimum > maximum:
        minimum, maximum = maximum, minimum

    if minimum <= value <= maximum:
        return 100.0

    distance = minimum - value if value < minimum else value - maximum
    return round(clamp(100 - distance * outside_decay), 1)


def rainfall_match_score(annual_rainfall, minimum, maximum):
    """Rainfall score with a relative penalty outside the ECOCROP range."""
    if pd.isna(minimum) or pd.isna(maximum):
        return None

    minimum = max(float(minimum), 0.0)
    maximum = max(float(maximum), minimum)

    if minimum <= annual_rainfall <= maximum:
        return 100.0

    if annual_rainfall < minimum:
        if minimum == 0:
            return 100.0
        shortage_ratio = (minimum - annual_rainfall) / minimum
        return round(clamp(100 - shortage_ratio * 100), 1)

    if maximum == 0:
        return 0.0

    excess_ratio = (annual_rainfall - maximum) / maximum
    return round(clamp(100 - excess_ratio * 75), 1)


def restoration_relevance_score(uses):
    """Score only what the ECOCROP use descriptors explicitly support."""
    if not isinstance(uses, str) or not uses.strip():
        return 35.0

    text = uses.lower()
    keyword_scores = {
        "revegetation": 100,
        "erosion control": 98,
        "pioneer": 90,
        "agroforestry": 88,
        "shade & shelter": 78,
        "manure/fertilizer": 68,
        "firebreaks": 65,
        "fuelwood": 48,
        "ornamental/turf": 30,
    }

    matched = [score for key, score in keyword_scores.items() if key in text]
    if not matched:
        return 45.0

    bonus = min(8, max(0, len(matched) - 1) * 2)
    return float(min(100, max(matched) + bonus))


def extract_best_for(uses):
    if not isinstance(uses, str) or not uses.strip():
        return ["Environmental suitability candidate"]

    items = [item.strip() for item in uses.split("|") if item.strip()]
    priority = [
        "revegetation",
        "erosion control",
        "pioneer",
        "agroforestry",
        "shade & shelter",
    ]

    ordered = []
    for wanted in priority:
        for item in items:
            if wanted in item.lower() and item not in ordered:
                ordered.append(item)

    for item in items:
        if item not in ordered:
            ordered.append(item)

    return ordered[:3] or ["Environmental suitability candidate"]


def gbif_local_occurrence_count(scientific_name: str, lat: float, lon: float):
    """
    Check nearby GBIF occurrence records in an approximately 150-200 km box.
    This is evidence of nearby occurrence, NOT proof that a species is native.
    Returns None if GBIF is unavailable.
    """
    radius_deg = 1.5
    min_lat = max(-89.9, lat - radius_deg)
    max_lat = min(89.9, lat + radius_deg)
    min_lon = max(-179.9, lon - radius_deg)
    max_lon = min(179.9, lon + radius_deg)

    geometry = (
        f"POLYGON(({min_lon} {min_lat},"
        f"{max_lon} {min_lat},"
        f"{max_lon} {max_lat},"
        f"{min_lon} {max_lat},"
        f"{min_lon} {min_lat}))"
    )

    try:
        response = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params={
                "scientificName": scientific_name,
                "geometry": geometry,
                "hasCoordinate": "true",
                "occurrenceStatus": "PRESENT",
                "limit": 0,
            },
            timeout=8,
        )
        response.raise_for_status()
        return int(response.json().get("count", 0))
    except Exception:
        return None



def _clean_media_text(value):
    """Remove HTML from attribution metadata while keeping readable credit text."""
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


@lru_cache(maxsize=2048)
def resolve_species_image(scientific_name: str):
    """
    Resolve a real species image using:
      1) GBIF occurrence multimedia
      2) Wikimedia Commons fallback

    Returns attribution/license metadata with the image.
    No generic plant photo is substituted when a species image cannot be verified.
    """
    name = (scientific_name or "").strip()
    if not name:
        return None

    # ---------- 1. GBIF ----------
    try:
        response = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params={
                "scientificName": name,
                "mediaType": "StillImage",
                "occurrenceStatus": "PRESENT",
                "limit": 20,
            },
            timeout=10,
        )
        response.raise_for_status()

        for occurrence in response.json().get("results", []):
            for media in occurrence.get("media", []) or []:
                identifier = media.get("identifier")
                media_type = str(media.get("type", "")).lower()

                if (
                    isinstance(identifier, str)
                    and identifier.startswith(("http://", "https://"))
                    and ("stillimage" in media_type or "image" in media_type or not media_type)
                ):
                    return {
                        "scientific_name": name,
                        "image_url": identifier,
                        "thumbnail_url": identifier,
                        "source": "GBIF",
                        "source_url": occurrence.get("references") or media.get("references"),
                        "license": media.get("license"),
                        "creator": _clean_media_text(
                            media.get("creator")
                            or occurrence.get("recordedBy")
                            or occurrence.get("identifiedBy")
                        ),
                        "title": _clean_media_text(media.get("title")),
                        "gbif_occurrence_key": occurrence.get("key"),
                        "verified_species_query": True,
                    }
    except Exception:
        pass

    # ---------- 2. Wikimedia Commons ----------
    try:
        response = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": name,
                "gsrnamespace": 6,  # File namespace
                "gsrlimit": 12,
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata",
                "iiurlwidth": 1000,
                "iiextmetadatafilter": "Artist|Credit|LicenseShortName|LicenseUrl|ImageDescription",
                "origin": "*",
            },
            headers={
                "User-Agent": "GAIA-Hackathon/0.7 environmental decision-support prototype"
            },
            timeout=10,
        )
        response.raise_for_status()
        pages = list((response.json().get("query", {}).get("pages", {}) or {}).values())

        genus_species = " ".join(name.lower().split()[:2])
        bad_words = (
            "map", "distribution", "range", "herbarium", "drawing",
            "illustration", "diagram", "icon", "logo"
        )

        ranked = []
        for page in pages:
            title = str(page.get("title", ""))
            info_list = page.get("imageinfo") or []
            if not info_list:
                continue

            info = info_list[0]
            mime = str(info.get("mime", "")).lower()
            image_url = info.get("thumburl") or info.get("url")
            if not image_url or not mime.startswith("image/"):
                continue

            title_lower = title.lower().replace("_", " ")
            score = 0
            if genus_species and genus_species in title_lower:
                score += 100

            pieces = genus_species.split()
            score += sum(15 for piece in pieces if piece and piece in title_lower)
            score -= sum(30 for word in bad_words if word in title_lower)

            ranked.append((score, page, info))

        if ranked:
            ranked.sort(key=lambda item: item[0], reverse=True)
            _, page, info = ranked[0]
            meta = info.get("extmetadata", {}) or {}

            def meta_value(key):
                value = meta.get(key, {})
                return _clean_media_text(value.get("value")) if isinstance(value, dict) else None

            return {
                "scientific_name": name,
                "image_url": info.get("thumburl") or info.get("url"),
                "thumbnail_url": info.get("thumburl") or info.get("url"),
                "source": "Wikimedia Commons",
                "source_url": info.get("descriptionurl"),
                "license": meta_value("LicenseShortName"),
                "license_url": (
                    meta.get("LicenseUrl", {}).get("value")
                    if isinstance(meta.get("LicenseUrl"), dict)
                    else None
                ),
                "creator": meta_value("Artist") or meta_value("Credit"),
                "title": page.get("title"),
                "description": meta_value("ImageDescription"),
                "verified_species_query": True,
            }
    except Exception:
        pass

    return None


@app.get("/species-image")
def species_image(name: str):
    """
    Return a species-specific image plus source/license attribution.
    GBIF is preferred; Wikimedia Commons is used as fallback.
    """
    clean_name = (name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Species name is required.")

    result = resolve_species_image(clean_name)

    if result is None:
        return {
            "scientific_name": clean_name,
            "image_url": None,
            "thumbnail_url": None,
            "source": None,
            "license": None,
            "creator": None,
            "message": "No verified species image was found from GBIF or Wikimedia Commons.",
        }

    return result


def locality_score_from_count(count):
    if count is None:
        return None
    if count >= 50:
        return 100.0
    if count >= 10:
        return 88.0
    if count >= 3:
        return 72.0
    if count >= 1:
        return 55.0
    return 0.0


def build_species_candidate(row, annual_climate, soil_ph=None):
    temperature = annual_climate["annual_mean_temperature_c"]
    rainfall = annual_climate["annual_rainfall_mm"]

    temp_score = range_match_score(
        temperature,
        row["temp_min_c"],
        row["temp_max_c"],
        outside_decay=8,
    )

    rain_score = rainfall_match_score(
        rainfall,
        row["rainfall_min_mm_year"],
        row["rainfall_max_mm_year"],
    )

    if temp_score is None or rain_score is None:
        return None

    ph_score = None
    if soil_ph is not None:
        ph_score = range_match_score(
            soil_ph,
            row["ph_min"],
            row["ph_max"],
            outside_decay=20,
        )

    benefit_score = restoration_relevance_score(row.get("uses"))

    completeness = 0
    for column in [
        "temp_min_c",
        "temp_max_c",
        "rainfall_min_mm_year",
        "rainfall_max_mm_year",
        "ph_min",
        "ph_max",
        "uses",
    ]:
        value = row.get(column)
        if not pd.isna(value) and str(value).strip():
            completeness += 1
    completeness_score = completeness / 7 * 100

    if soil_ph is not None and ph_score is not None:
        environmental_score = (
            temp_score * 0.35
            + rain_score * 0.30
            + ph_score * 0.20
            + benefit_score * 0.10
            + completeness_score * 0.05
        )
    else:
        environmental_score = (
            temp_score * 0.45
            + rain_score * 0.35
            + benefit_score * 0.15
            + completeness_score * 0.05
        )

    return {
        "scientific_name": str(row["scientific_name"]),
        "common_name": str(row["scientific_name"]),
        "family": None if pd.isna(row.get("family")) else str(row.get("family")),
        "environmental_score": round(clamp(environmental_score), 1),
        "temperature_match": temp_score,
        "rainfall_match": rain_score,
        "soil_ph_match": ph_score,
        "restoration_relevance": benefit_score,
        "data_completeness": round(completeness_score, 1),
        "best_for": extract_best_for(row.get("uses")),
        "uses": [] if pd.isna(row.get("uses")) else [
            item.strip() for item in str(row.get("uses")).split("|") if item.strip()
        ],
        "requirements": {
            "temperature_c": {
                "min": None if pd.isna(row["temp_min_c"]) else float(row["temp_min_c"]),
                "max": None if pd.isna(row["temp_max_c"]) else float(row["temp_max_c"]),
            },
            "annual_rainfall_mm": {
                "min": None if pd.isna(row["rainfall_min_mm_year"]) else float(row["rainfall_min_mm_year"]),
                "max": None if pd.isna(row["rainfall_max_mm_year"]) else float(row["rainfall_max_mm_year"]),
            },
            "soil_ph": {
                "min": None if pd.isna(row["ph_min"]) else float(row["ph_min"]),
                "max": None if pd.isna(row["ph_max"]) else float(row["ph_max"]),
            },
        },
        "source": str(row.get("source", "FAO ECOCROP-derived data")),
    }


def ecological_recommendation_gate(candidate, locality_count, soil_ph=None):
    """
    Separate climate suitability from ecological recommendation.

    A species can match temperature/rainfall and still be inappropriate for
    a restoration project. GAIA therefore refuses to turn climate fit into
    an ecological recommendation when native status, invasive risk,
    salinity/hydrology, or ecosystem compatibility are still unverified.
    """
    climate_fit = candidate["environmental_score"] >= 70
    nearby_evidence = locality_count is not None and locality_count > 0

    missing_ecology = [
        "verified native status",
        "invasive-risk assessment",
        "ecosystem/land-cover classification",
        "site salinity and hydrology",
    ]
    if soil_ph is None:
        missing_ecology.append("measured soil pH")

    if climate_fit and nearby_evidence:
        return {
            "climate_suitable": True,
            "ecologically_recommended": False,
            "status": "climate_suitable_ecology_unverified",
            "statement": (
                "This species may be able to survive here, but GAIA does not "
                "recommend it for this ecosystem yet."
            ),
            "reason": (
                "Climate fit and nearby occurrence are not enough to establish "
                "ecological appropriateness."
            ),
            "missing_evidence": missing_ecology,
        }

    if climate_fit:
        return {
            "climate_suitable": True,
            "ecologically_recommended": False,
            "status": "climate_suitable_locality_unverified",
            "statement": (
                "This species may be able to survive here, but GAIA does not "
                "recommend it for this ecosystem yet."
            ),
            "reason": (
                "The climate match is promising, but nearby occurrence and "
                "ecological suitability are not sufficiently verified."
            ),
            "missing_evidence": ["nearby occurrence evidence"] + missing_ecology,
        }

    return {
        "climate_suitable": False,
        "ecologically_recommended": False,
        "status": "not_recommended",
        "statement": (
            "GAIA does not recommend this species because the current evidence "
            "does not show a strong enough environmental match."
        ),
        "reason": "Environmental suitability is below GAIA's provisional threshold.",
        "missing_evidence": missing_ecology,
    }


def finalize_species_candidate(candidate, locality_count, soil_ph=None):
    locality_score = locality_score_from_count(locality_count)

    if locality_score is None:
        final_score = candidate["environmental_score"]
        locality_status = "unverified"
    else:
        final_score = (
            candidate["environmental_score"] * 0.75
            + locality_score * 0.25
        )
        locality_status = (
            "strong nearby occurrence evidence"
            if locality_count >= 10
            else "some nearby occurrence evidence"
            if locality_count >= 1
            else "no nearby GBIF occurrence found"
        )

    reasons = []
    warnings = []

    if candidate["temperature_match"] >= 85:
        reasons.append("Annual temperature closely matches the species' ECOCROP range")
    elif candidate["temperature_match"] < 50:
        warnings.append("Temperature is outside the preferred ECOCROP range")

    if candidate["rainfall_match"] >= 85:
        reasons.append("Annual rainfall closely matches the species' ECOCROP range")
    elif candidate["rainfall_match"] < 50:
        warnings.append("Rainfall is outside the preferred ECOCROP range")

    if candidate["restoration_relevance"] >= 80:
        reasons.append("FAO ECOCROP use descriptors indicate strong restoration relevance")

    if locality_count is not None and locality_count > 0:
        reasons.append(
            f"GBIF reports {locality_count} georeferenced occurrence record(s) near the selected area"
        )
    elif locality_count == 0:
        warnings.append("No nearby GBIF occurrence record was found in the search box")
    else:
        warnings.append("GBIF locality evidence could not be verified during this request")

    warnings.append(
        "Nearby occurrence is not proof of native status; local ecological validation is still required"
    )

    ecological_gate = ecological_recommendation_gate(
        candidate=candidate,
        locality_count=locality_count,
        soil_ph=soil_ph,
    )

    # Backward-compatible profile keys so the current frontend keeps rendering.
    profile = {
        "heat_tolerance": round(candidate["temperature_match"], 1),
        "drought_tolerance": round(candidate["rainfall_match"], 1),
        "salinity_tolerance": None,
        "water_efficiency": round(candidate["rainfall_match"], 1),
        "biodiversity_value": round(candidate["restoration_relevance"], 1),
        "restoration_value": round(candidate["restoration_relevance"], 1),
        "temperature_match": round(candidate["temperature_match"], 1),
        "rainfall_match": round(candidate["rainfall_match"], 1),
        "soil_ph_match": candidate["soil_ph_match"],
        "locality_evidence": locality_score,
    }

    return {
        "common_name": candidate["common_name"],
        "scientific_name": candidate["scientific_name"],
        "family": candidate["family"],
        "gaia_score": round(clamp(final_score), 1),
        "best_for": candidate["best_for"],
        "uses": candidate["uses"],
        "reasons": reasons,
        "warnings": warnings,
        "profile": profile,
        "environmental_requirements": candidate["requirements"],
        "locality_evidence": {
            "status": locality_status,
            "gbif_occurrence_count": locality_count,
            "search_area": "approximately +/-1.5 degrees around the selected point",
            "source": "GBIF Occurrence API",
            "native_status_proven": False,
        },
        "ecological_recommendation": ecological_gate,
        "data_source": candidate["source"],
    }


@app.get("/species")
def recommend_species(
    lat: float,
    lon: float,
    soil_ph: float | None = None,
    limit: int = 5,
):
    """
    GAIA Species Intelligence v0.7

    1. Reads the FAO ECOCROP-derived species database.
    2. Matches annual NASA POWER temperature and rainfall.
    3. Optionally matches user-supplied soil pH.
    4. Rewards restoration-relevant ECOCROP uses.
    5. Checks nearby GBIF occurrence evidence for top candidates.

    GBIF occurrence evidence helps with locality, but does not prove nativeness.
    """
    try:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(status_code=400, detail="Invalid latitude or longitude")

        if soil_ph is not None and not (0 <= soil_ph <= 14):
            raise HTTPException(status_code=400, detail="soil_ph must be between 0 and 14")

        limit = max(1, min(limit, 10))

        climate_30d = fetch_nasa_climate(lat=lat, lon=lon)
        climate_risk = calculate_environmental_risk(
            avg_temp=climate_30d["average_temperature"],
            max_temp=climate_30d["maximum_temperature"],
            rainfall=climate_30d["total_rainfall"],
            humidity=climate_30d["average_humidity"],
        )

        annual_climate = fetch_nasa_species_climate(lat=lat, lon=lon)
        df = load_species_database()

        candidates = []
        for _, row in df.iterrows():
            candidate = build_species_candidate(
                row=row,
                annual_climate=annual_climate,
                soil_ph=soil_ph,
            )
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: item["environmental_score"],
            reverse=True,
        )

        # Locality checks are intentionally limited to the strongest
        # environmental candidates to keep the endpoint responsive.
        locality_pool_size = min(max(limit * 3, 12), len(candidates))
        locality_pool = candidates[:locality_pool_size]

        finalized = []
        for candidate in locality_pool:
            occurrence_count = gbif_local_occurrence_count(
                scientific_name=candidate["scientific_name"],
                lat=lat,
                lon=lon,
            )
            finalized.append(
                finalize_species_candidate(
                    candidate,
                    occurrence_count,
                    soil_ph=soil_ph,
                )
            )

        finalized.sort(
            key=lambda item: item["gaia_score"],
            reverse=True,
        )

        return {
            "location": {
                "latitude": lat,
                "longitude": lon,
            },
            "environmental_context": climate_risk,
            "species_matching_climate": {
                "period": {
                    "start": str(annual_climate["start_date"]),
                    "end": str(annual_climate["end_date"]),
                },
                "annual_mean_temperature_c": round(
                    annual_climate["annual_mean_temperature_c"], 2
                ),
                "annual_rainfall_mm": round(
                    annual_climate["annual_rainfall_mm"], 2
                ),
                "soil_ph": soil_ph,
                "climate_source": "NASA POWER",
            },
            "database": {
                "species_records": int(len(df)),
                "environmentally_evaluated": int(len(candidates)),
                "locality_checked": int(len(finalized)),
                "source": "FAO ECOCROP-derived DwC-A measurement data",
            },
            "recommendation": {
                "strategy": (
                    "First identify species that can plausibly tolerate local conditions, "
                    "then keep ecological recommendation separate until native status, "
                    "invasive risk, ecosystem compatibility, salinity and hydrology are verified."
                ),
                "top_species": finalized[:limit],
            },
            "important_note": (
                "GAIA v0.4 separates climate suitability from ecological recommendation. It uses real environmental ranges and nearby GBIF occurrence "
                "evidence. Occurrence does not prove that a species is native, safe, "
                "or appropriate for a specific ecosystem. Soil salinity, hydrology, "
                "invasive risk, land use, and native-status validation should be added "
                "before real-world planting decisions."
            ),
            "engine": "GAIA Species Intelligence v0.7",
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate species recommendations: {error}",
        )


# =========================
# GAIA AI REASONING LAYER
# OpenAI Responses API
# =========================

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY was not found. Add it to the .env file next to main.py."
        )
    return OpenAI(api_key=api_key)


def _clean_ai_json(text: str):
    """Parse JSON returned by the model, tolerating accidental markdown fences."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def generate_gaia_ai_analysis(species_result, intervention_result, ecosystem_result):
    top_species = species_result["recommendation"]["top_species"]
    context = {
        "location": species_result["location"],
        "environmental_risk": species_result["environmental_context"],
        "annual_climate": species_result["species_matching_climate"],
        "candidate_species": top_species,
        "intervention": intervention_result["recommended_intervention"],
        "land_cover_evidence": ecosystem_result["land_cover"],
        "ecosystem_intervention_guidance": ecosystem_result["intervention_guidance"],
        "ecosystem_evidence_note": ecosystem_result["confidence_note"],
    }

    instructions = """
You are the reasoning layer of GAIA, an environmental decision-support prototype.
Use ONLY the supplied structured evidence. Do not invent native status, salinity tolerance,
soil conditions, hydrology, invasive risk, biodiversity claims, ecosystem type, or scientific
facts that are not present in the input. GBIF occurrence is evidence of nearby observation,
not proof of native status. ECOCROP ranges describe environmental suitability, not ecological safety.

CRITICAL DECISION RULE:
A plant that can tolerate the climate is NOT automatically a plant GAIA should recommend for
the ecosystem. Keep "can survive" separate from "should be planted here". If climate suitability
is strong but ecosystem compatibility/native status/invasive risk/salinity/hydrology are not
verified, set recommend_for_ecosystem=false and use this sentence in the statement:
"This species may be able to survive here, but GAIA does not recommend it for this ecosystem yet."

You may identify the strongest climate candidate, but you must NOT turn it into an ecological
recommendation unless the supplied evidence actually supports ecological appropriateness.

Return valid JSON only, with exactly these keys:
{
  "best_climate_candidate": {
    "scientific_name": string,
    "why": string
  },
  "ecosystem_verdict": {
    "can_survive": true | false | null,
    "recommend_for_ecosystem": true | false | null,
    "statement": string,
    "reason": string
  },
  "tradeoffs": [string],
  "alternative": {"scientific_name": string, "why": string},
  "confidence": "high" | "medium" | "low",
  "missing_data": [string],
  "decision_summary": string
}

Confidence must reflect evidence quality, not fluency. Do not recommend a species outside the
supplied candidate list. ESA WorldCover evidence may be used to identify the observed land-cover class and a cautious
ecosystem interpretation. Treat this as an ecosystem proxy, NOT proof of complete ecosystem type,
native community composition, salinity, hydrology, or habitat condition. Even when land cover is
known, do not set recommend_for_ecosystem=true unless the supplied evidence supports the species'
ecological appropriateness.
""".strip()

    client = get_openai_client()
    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=instructions,
        input=json.dumps(context, ensure_ascii=False),
    )

    analysis = _clean_ai_json(response.output_text)

    allowed_names = {item["scientific_name"] for item in top_species}
    climate_choice = analysis.get("best_climate_candidate") or {}
    choice_name = climate_choice.get("scientific_name")
    if choice_name not in allowed_names:
        raise ValueError("AI returned a climate candidate outside GAIA's verified candidate list")

    alternative = analysis.get("alternative") or {}
    alt_name = alternative.get("scientific_name")
    if alt_name and alt_name not in allowed_names:
        raise ValueError("AI returned an alternative outside GAIA's verified candidate list")

    verdict = analysis.get("ecosystem_verdict") or {}
    if verdict.get("recommend_for_ecosystem") is True:
        # v0.4 currently has no verified native/invasive/ecosystem layer, so a positive
        # ecological planting recommendation would overstate the evidence.
        verdict["recommend_for_ecosystem"] = False
        verdict["statement"] = (
            "This species may be able to survive here, but GAIA does not "
            "recommend it for this ecosystem yet."
        )
        verdict["reason"] = (
            "GAIA does not yet have enough verified native-status, "
            "invasive-risk, salinity and hydrology evidence for a planting recommendation."
        )
        analysis["ecosystem_verdict"] = verdict

    return analysis


@app.get("/ai-analysis")
def get_ai_analysis(
    lat: float,
    lon: float,
    soil_ph: float | None = None,
    limit: int = 5,
):
    """
    GAIA AI layer: deterministic environmental evidence first, AI explanation second.
    The model may compare and explain candidates but cannot add unsupported species.
    """
    try:
        species_result = recommend_species(
            lat=lat,
            lon=lon,
            soil_ph=soil_ph,
            limit=max(2, min(limit, 5)),
        )
        intervention_result = get_intervention(lat=lat, lon=lon)
        ecosystem_result = get_ecosystem(lat=lat, lon=lon)
        ai_analysis = generate_gaia_ai_analysis(
            species_result=species_result,
            intervention_result=intervention_result,
            ecosystem_result=ecosystem_result,
        )

        return {
            "location": species_result["location"],
            "evidence": {
                "environmental_context": species_result["environmental_context"],
                "species_matching_climate": species_result["species_matching_climate"],
                "top_species": species_result["recommendation"]["top_species"],
                "recommended_intervention": intervention_result["recommended_intervention"],
                "land_cover": ecosystem_result["land_cover"],
                "ecosystem_intervention_guidance": ecosystem_result["intervention_guidance"],
                "ecosystem_source": ecosystem_result["source"],
            },
            "ai_analysis": ai_analysis,
            "decision_framework": {
                "climate_suitability": "Can this species plausibly tolerate the measured climate?",
                "ecological_recommendation": "Should this species be used in this ecosystem?",
                "current_ecosystem_status": "land-cover proxy connected; ecological community still requires validation",
                "land_cover_class": ecosystem_result["land_cover"]["class_name"],
                "ecosystem_interpretation": ecosystem_result["land_cover"]["ecosystem_interpretation"],
            },
            "architecture": "Data-grounded hybrid AI: NASA POWER + ESA WorldCover + ECOCROP + GBIF + ecosystem-aware deterministic intervention logic + OpenAI reasoning",
            "model": "gpt-5.6-luna",
            "safety_note": (
                "GAIA v0.6 combines ecosystem-aware intervention logic with ESA WorldCover while keeping survival/climate "
                "suitability separate from ecological recommendation. Land cover alone does not "
                "verify native status, invasive risk, salinity, hydrology, or ecological safety."
            ),
            "engine": "GAIA Hybrid AI Decision Engine v0.6",
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate GAIA AI analysis: {error}",
        )


@app.get("/intervention")
def get_intervention(lat: float, lon: float):
    """
    GAIA v0.6 ecosystem-aware intervention engine.

    Climate risk determines urgency, while ESA WorldCover land cover changes
    the intervention type so GAIA does not default to tree planting.
    """
    climate = fetch_nasa_climate(lat, lon)
    risk = calculate_environmental_risk(
        avg_temp=climate["average_temperature"],
        max_temp=climate["maximum_temperature"],
        rainfall=climate["total_rainfall"],
        humidity=climate["average_humidity"],
    )
    ecosystem = get_ecosystem(lat=lat, lon=lon)

    heat = risk["heat_stress"]["score"]
    water = risk["water_stress"]["score"]
    drought = risk["drought_pressure"]["score"]
    overall = risk["overall_climate_risk"]["score"]

    code = ecosystem["land_cover"]["class_code"]
    class_name = ecosystem["land_cover"]["class_name"]

    if overall >= 80:
        priority = "Critical"
    elif overall >= 60:
        priority = "High"
    elif overall >= 40:
        priority = "Moderate"
    else:
        priority = "Preventive"

    # Ecosystem-first decision logic. Climate risk controls urgency, but land
    # cover controls what kind of intervention is ecologically sensible.
    if code == 50:  # Built-up
        intervention = {
            "title": "Urban Heat & Water Resilience",
            "priority": priority,
            "strategy": (
                "Reduce urban heat and water stress using shade, permeable surfaces, "
                "cooler public-space design, and water-efficient greening rather than "
                "treating the site as a natural restoration area."
            ),
            "actions": [
                "Protect and expand shade where locally appropriate",
                "Use permeable surfaces and soil-water retention measures",
                "Prioritize water-efficient urban vegetation",
                "Protect existing mature vegetation",
                "Target heat-exposed streets and public spaces before large planting programs",
            ],
            "avoid": [
                "Treating built-up land as a natural ecosystem restoration site",
                "Dense high-water-demand planting",
                "Large-scale planting without soil, salinity, and infrastructure checks",
            ],
        }

    elif code == 60:  # Bare / sparse
        intervention = {
            "title": "Arid Land Stabilization & Sparse Vegetation Recovery",
            "priority": priority,
            "strategy": (
                "Stabilize degraded soil, reduce erosion, retain scarce water, and recover "
                "sparse locally appropriate vegetation only where ecological evidence supports it."
            ),
            "actions": [
                "Prioritize erosion control and soil stabilization",
                "Increase infiltration and micro-catchment water retention where feasible",
                "Protect naturally sparse vegetation from disturbance",
                "Use low-water-demand locally appropriate vegetation only after ecological validation",
                "Check salinity and groundwater constraints before scaling restoration",
            ],
            "avoid": [
                "Dense tree planting as a default solution",
                "High-water-demand vegetation",
                "Converting naturally bare or sparsely vegetated habitat without ecological justification",
            ],
        }

    elif code == 40:  # Cropland
        intervention = {
            "title": "Water-Smart Agricultural Resilience",
            "priority": priority,
            "strategy": (
                "Improve agricultural resilience through water efficiency, soil recovery, and "
                "climate-adapted land management while protecting productive land use."
            ),
            "actions": [
                "Reduce irrigation losses and improve water-use efficiency",
                "Improve soil organic matter and moisture retention",
                "Protect field margins and existing vegetation",
                "Consider agroforestry only where locally and agronomically appropriate",
                "Monitor salinity and groundwater conditions",
            ],
            "avoid": [
                "Converting productive cropland into dense tree plantations",
                "Water-intensive planting without water-budget analysis",
                "Ignoring farmer and land-use constraints",
            ],
        }

    elif code == 90:  # Herbaceous wetland
        intervention = {
            "title": "Wetland Hydrology & Habitat Recovery",
            "priority": priority,
            "strategy": (
                "Restore wetland function by prioritizing hydrology, water quality, salinity, and "
                "native wetland vegetation before considering terrestrial planting."
            ),
            "actions": [
                "Assess water flow and hydroperiod",
                "Measure salinity and water quality",
                "Protect or recover native wetland vegetation",
                "Reduce hydrological disruption",
                "Use planting only as part of a validated wetland restoration plan",
            ],
            "avoid": [
                "Tree-first restoration",
                "Terrestrial planting that alters wetland water balance",
                "Species introduction without verified native/ecosystem compatibility",
            ],
        }

    elif code == 80:  # Permanent water
        intervention = {
            "title": "Aquatic & Riparian System Protection",
            "priority": priority,
            "strategy": (
                "Prioritize water quality, hydrology, shoreline condition, and riparian habitat "
                "rather than terrestrial planting inside the water body."
            ),
            "actions": [
                "Assess water quality and hydrological condition",
                "Protect shoreline and riparian buffers",
                "Reduce erosion and pollutant inputs",
                "Restore riparian vegetation only where locally appropriate",
            ],
            "avoid": [
                "Terrestrial planting inside permanent-water pixels",
                "Ignoring upstream hydrological drivers",
            ],
        }

    elif code == 30:  # Grassland
        intervention = {
            "title": "Grassland Recovery & Erosion Control",
            "priority": priority,
            "strategy": (
                "Protect grassland structure, reduce erosion, and recover locally appropriate "
                "herbaceous vegetation instead of assuming tree planting is required."
            ),
            "actions": [
                "Protect existing grass cover",
                "Reduce soil erosion and disturbance",
                "Support locally appropriate herbaceous recovery",
                "Improve soil moisture retention where feasible",
            ],
            "avoid": [
                "Converting grassland to dense woodland without ecological justification",
                "High-water-demand planting",
            ],
        }

    elif code == 20:  # Shrubland
        intervention = {
            "title": "Shrubland Protection & Recovery",
            "priority": priority,
            "strategy": (
                "Protect existing shrubland, stabilize soils, and recover locally appropriate "
                "native shrub communities where degradation is confirmed."
            ),
            "actions": [
                "Protect existing shrub cover",
                "Reduce erosion and disturbance",
                "Recover locally appropriate shrubs where needed",
                "Conserve scarce soil moisture",
            ],
            "avoid": [
                "Replacing shrubland with dense tree plantations",
                "Introducing ecologically unverified species",
            ],
        }

    elif code == 10:  # Tree cover
        intervention = {
            "title": "Existing Tree-Cover Protection & Targeted Restoration",
            "priority": priority,
            "strategy": (
                "Protect existing tree cover first and restore only degraded gaps using locally "
                "appropriate species and site-specific ecological evidence."
            ),
            "actions": [
                "Protect existing mature tree cover",
                "Identify degradation before adding new planting",
                "Restore gaps with locally appropriate species",
                "Monitor soil moisture and heat stress",
            ],
            "avoid": [
                "Replacing established communities with climate-suitable but ecologically unverified species",
                "Planting where existing vegetation is already healthy",
            ],
        }

    elif code == 95:  # Mangroves
        intervention = {
            "title": "Mangrove Hydrology & Native Habitat Recovery",
            "priority": priority,
            "strategy": (
                "Protect tidal connectivity, sediment processes, and verified native mangrove habitat "
                "before any planting intervention."
            ),
            "actions": [
                "Assess tidal connectivity and hydrology",
                "Protect existing mangrove stands",
                "Assess sediment and salinity conditions",
                "Use verified native mangrove restoration only when needed",
            ],
            "avoid": [
                "Introducing terrestrial non-mangrove species",
                "Planting without restoring hydrological drivers",
            ],
        }

    elif code in {70, 100}:  # Snow/ice or moss/lichen
        intervention = {
            "title": "Fragile Surface Protection",
            "priority": priority,
            "strategy": (
                "Minimize disturbance and protect the existing land-cover system; vegetation planting "
                "is not the default intervention."
            ),
            "actions": [
                "Minimize physical disturbance",
                "Monitor environmental change",
                "Protect existing surface communities",
            ],
            "avoid": [
                "Tree planting without clear ecological evidence",
                "Converting naturally non-forested habitat",
            ],
        }

    else:
        # Fallback combines climate pressure with conservative management.
        if water >= 80 and drought >= 80:
            title = "Drought-Resilient Ecosystem Management"
        elif heat >= 80:
            title = "Heat-Resilient Ecosystem Management"
        else:
            title = "Preventive Ecosystem Management"
        intervention = {
            "title": title,
            "priority": priority,
            "strategy": "Validate local ecosystem conditions before choosing a restoration action.",
            "actions": [
                "Protect existing habitat",
                "Improve soil and water resilience where needed",
                "Validate local ecological conditions before planting",
            ],
            "avoid": [
                "Using climate suitability alone as proof of ecological appropriateness",
            ],
        }

    return {
        "location": {"latitude": lat, "longitude": lon},
        "land_cover_context": {
            "class_code": code,
            "class_name": class_name,
            "ecosystem_interpretation": ecosystem["land_cover"]["ecosystem_interpretation"],
            "source": ecosystem["source"]["name"],
        },
        "environmental_risk": risk,
        "overall_risk": {
            "score": overall,
            "level": risk["overall_climate_risk"]["level"],
        },
        "recommended_intervention": intervention,
        "method": "GAIA ecosystem-aware intervention engine v0.6",
        "disclaimer": (
            "This is an environmental decision-support prototype. ESA WorldCover is a land-cover "
            "proxy, not a full ecological assessment. Validate local soil, hydrology, salinity, "
            "native status, invasive risk, biodiversity, and land-use constraints before action."
        ),
    }
