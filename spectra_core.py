"""
Shared calculation logic for the RTGM and IS code spectra tools.
"""

import csv
import sys
from pathlib import Path

import numpy as np
import scipy.io
from scipy import stats
from scipy.interpolate import interp1d


MAT_FILE_NAME = "Hazard_curves_All_grid_points_in_India.mat"
CITY_DATABASE_FILE_NAMES = ("Indian_cities_geocoded.csv", "Indian_cities.csv", "india_cities.csv")
USER_CITY_LABEL = "User"

TP = np.array([
    0.010, 0.015, 0.020, 0.030, 0.040, 0.050, 0.060, 0.075, 0.090,
    0.100, 0.150, 0.200, 0.300, 0.400, 0.500, 0.600, 0.700, 0.750,
    0.800, 0.900, 1.000, 1.200, 1.500, 2.000, 2.500, 3.000, 5.000,
])

ZONE_FACTORS = {
    "VI": {"Z_475": 0.5, "Z_2475": 0.75},
    "V": {"Z_475": 0.333, "Z_2475": 0.5},
    "IV": {"Z_475": 0.233, "Z_2475": 0.35},
    "III": {"Z_475": 0.125, "Z_2475": 0.25},
    "II": {"Z_475": 0.075, "Z_2475": 0.15},
}

SITE_AMPLIFICATION = {
    "Metamorphic and volcanic rocks": 1.0,
    "Sedimentary rocks": 1.15,
    "Laterite layers": 1.35,
    "Alluvium": 1.5,
}

DEFAULT_CITY_COORDINATES = {
    "Ahmedabad": (23.0225, 72.5714),
    "Bengaluru": (12.9716, 77.5946),
    "Bhopal": (23.2599, 77.4126),
    "Bhubaneswar": (20.2961, 85.8245),
    "Chandigarh": (30.7333, 76.7794),
    "Chennai": (13.0827, 80.2707),
    "Delhi": (28.6139, 77.2090),
    "Guwahati": (26.2, 91.8),
    "Hyderabad": (17.3850, 78.4867),
    "Jaipur": (26.9124, 75.7873),
    "Kochi": (9.9312, 76.2673),
    "Kolkata": (22.5726, 88.3639),
    "Lucknow": (26.8467, 80.9462),
    "Mumbai": (19.0760, 72.8777),
    "Patna": (25.5941, 85.1376),
    "Pune": (18.5204, 73.8567),
    "Shillong": (25.5788, 91.8933),
    "Srinagar": (34.0837, 74.7973),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Visakhapatnam": (17.6868, 83.2185),
}


def resource_path(filename):
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).resolve().parent
    return base_path / filename


def risk_integral(x, y1, y2):
    return np.trapezoid(y1 * y2, x)


def is_spectra(periods):
    spectra = np.zeros(len(periods))
    for i, period in enumerate(periods):
        if period < 0.01:
            spectra[i] = 1.0
        elif period < 0.1:
            spectra[i] = 1.0 + (50.0 / 3.0) * (period - 0.01)
        elif period < 0.4:
            spectra[i] = 2.5
        elif period < 6.0:
            spectra[i] = 1 / period
        else:
            spectra[i] = 6 / period**2
    return spectra


def spectral_acceleration_at_maf(hazard, sa_values, target_maf):
    order = np.argsort(hazard)
    hazard_sorted = hazard[order]
    sa_sorted = sa_values[order]
    hazard_unique, unique_indices = np.unique(hazard_sorted, return_index=True)
    sa_unique = sa_sorted[unique_indices]
    linfit_hazard = interp1d(
        hazard_unique,
        sa_unique,
        kind="linear",
        bounds_error=False,
        fill_value="extrapolate",
    )
    return max(float(linfit_hazard(target_maf)), 0.0)


def collapse_risk_for_rtgm(sa_values, hazard, rtgm, beta):
    median = np.log(1.5 * rtgm) + 1.28 * beta
    fragility_pdf = stats.lognorm.pdf(sa_values, beta, scale=np.exp(median))
    annual_risk = risk_integral(sa_values, hazard, fragility_pdf)
    return 1 - (1 - annual_risk) ** 50


def load_hazard_data():
    mat_path = resource_path(MAT_FILE_NAME)
    if not mat_path.exists():
        raise FileNotFoundError(f"Could not find {MAT_FILE_NAME}")

    mat_data = scipy.io.loadmat(mat_path)
    return {
        "lat": mat_data["LatIndia"][:, 0],
        "lon": mat_data["LongIndia"][:, 0],
        "sa": mat_data["int_g"][:, 0],
        "hazard_curves": mat_data["final_mean_hazard_curve_india"],
    }


def load_city_coordinates():
    cities = {
        city: {"latitude": lat, "longitude": lon, "zone": None}
        for city, (lat, lon) in DEFAULT_CITY_COORDINATES.items()
    }
    cities[USER_CITY_LABEL] = {"latitude": None, "longitude": None, "zone": None}

    for file_name in CITY_DATABASE_FILE_NAMES:
        csv_path = resource_path(file_name)
        if not csv_path.exists():
            continue

        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                city = (row.get("city") or row.get("City") or "").strip()
                if not city:
                    continue

                zone = (row.get("zone") or row.get("Zone") or "").strip() or None
                lat = row.get("latitude") or row.get("Latitude") or row.get("lat") or row.get("Lat")
                lon = row.get("longitude") or row.get("Longitude") or row.get("lon") or row.get("Long")
                city_data = cities.setdefault(city, {"latitude": None, "longitude": None, "zone": None})
                if zone in ZONE_FACTORS:
                    city_data["zone"] = zone
                if lat not in (None, "") and lon not in (None, ""):
                    city_data["latitude"] = float(lat)
                    city_data["longitude"] = float(lon)

        cities[USER_CITY_LABEL] = {"latitude": None, "longitude": None, "zone": None}
        return cities, file_name

    return cities, "built-in city list"


def calculate_spectra(hazard_data, latitude, longitude, site_amp, z_475, z_2475, beta):
    distances = np.sqrt((hazard_data["lat"] - latitude) ** 2 + (hazard_data["lon"] - longitude) ** 2)
    grid_index = distances.argmin()

    sa_values = hazard_data["sa"] * site_amp
    data_city = np.zeros((len(TP), len(sa_values)))
    for i in range(len(TP)):
        data_city[i] = hazard_data["hazard_curves"][0, i][grid_index]

    target_risk = 0.01
    rel_tol = 0.0001
    num_iter_limit = 1000

    dbe_maf = 1.0 - (1 - 0.1) ** (1 / 50)
    mce_maf = 1.0 - (1 - 0.02) ** (1 / 50)

    rtgm_all = np.zeros(len(TP))
    dbe_all = np.zeros(len(TP))
    mce_all = np.zeros(len(TP))

    for i in range(len(TP)):
        hazard = data_city[i]
        dbe_all[i] = spectral_acceleration_at_maf(hazard, sa_values, dbe_maf)
        mce_all[i] = spectral_acceleration_at_maf(hazard, sa_values, mce_maf)

        lb = 0.0
        ub = max(2 * dbe_all[i], sa_values[0])
        while collapse_risk_for_rtgm(sa_values, hazard, ub, beta) > target_risk:
            ub *= 2
            if ub > 10 * sa_values[-1]:
                raise RuntimeError(f"Could not bracket RTGM target risk at T = {TP[i]:.3f} s")

        count = 0
        init_err = 1.0
        while init_err > rel_tol * target_risk:
            rtgm = (lb + ub) / 2.0
            risk = collapse_risk_for_rtgm(sa_values, hazard, rtgm, beta)
            init_err = abs(risk - target_risk)

            if risk > target_risk:
                lb = rtgm
            else:
                ub = rtgm

            count += 1
            if count > num_iter_limit:
                raise RuntimeError(f"RTGM iteration limit exceeded at T = {TP[i]:.3f} s")

            rtgm_all[i] = rtgm

    return {
        "periods": TP,
        "is_475": z_475 * is_spectra(TP),
        "is_2475": z_2475 * is_spectra(TP),
        "dbe": dbe_all,
        "mce": mce_all,
        "rtgm": rtgm_all,
        "nearest_lat": hazard_data["lat"][grid_index],
        "nearest_lon": hazard_data["lon"][grid_index],
    }


def results_rows(results):
    return [
        {
            "Tp (s)": period,
            "IS 475 yr": is_475,
            "IS 2475 yr": is_2475,
            "PSHA 475 yr": dbe,
            "PSHA 2475 yr": mce,
            "RTGM": rtgm,
        }
        for period, is_475, is_2475, dbe, mce, rtgm in zip(
            results["periods"],
            results["is_475"],
            results["is_2475"],
            results["dbe"],
            results["mce"],
            results["rtgm"],
        )
    ]
