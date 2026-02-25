import pandas as pd
import math
from geopy.geocoders import Nominatim
import time
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

crime_df = pd.read_csv(
    os.path.join(BASE_DIR, "atlanta_crime.csv"),
    encoding="latin1"
)
crime_df = crime_df[["Latitude", "Longitude", "NIBRS_Offense", "event_watch", "Part"]]
crime_df.columns = crime_df.columns.str.strip()
crime_df["Latitude"] = pd.to_numeric(crime_df["Latitude"], errors="coerce")
crime_df["Longitude"] = pd.to_numeric(crime_df["Longitude"], errors="coerce")
crime_df = crime_df.dropna(subset=["Latitude", "Longitude"])

sexoffender_df = pd.read_csv(
    os.path.join(BASE_DIR, "sexoffender_geocoded.csv"),
    encoding="utf-8-sig"
)
sexoffender_df.columns = sexoffender_df.columns.str.strip()


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) *
            math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c



def crimes_within_radius(user_lat, user_lon, radius_km=0.25):

    lat_range = radius_km / 111
    lon_range = radius_km / (111 * math.cos(math.radians(user_lat)))

    filtered = crime_df[
        (crime_df["Latitude"] >= user_lat - lat_range) &
        (crime_df["Latitude"] <= user_lat + lat_range) &
        (crime_df["Longitude"] >= user_lon - lon_range) &
        (crime_df["Longitude"] <= user_lon + lon_range)
        ]

    nearby = []

    for _, row in filtered.iterrows():
        distance = haversine(
            user_lat,
            user_lon,
            row["Latitude"],
            row["Longitude"]
        )

        if distance <= radius_km:
            nearby.append(row)

    return pd.DataFrame(nearby)



def calculate_risk(user_lat, user_lon, time_of_day):

    nearby = crimes_within_radius(user_lat, user_lon)

    total = len(nearby)

    if total == 0:
        return 0, 0

    # How many nearby crimes happened in each watch period
    watch_counts = nearby["event_watch"].value_counts()
    crimes_in_watch = watch_counts.get(time_of_day, 0)

    # Fraction of nearby crimes that occurred during the user's watch period.
    # e.g. 0.7 means 70% of crimes here happened at this time of day.
    time_fraction = crimes_in_watch / total

    weighted_score = 0

    for _, crime in nearby.iterrows():

        if crime["Part"] == "Part I":
            weighted_score += 4
        else:
            weighted_score += 1

    # How dangerous this watch period is historically at this location
    location_time_multiplier = 0.3 + (time_fraction * 5.1)

    # Base multiplier by watch period — night is always riskier than day
    # regardless of local crime history
    base_time_multiplier = {
        "Day Watch":     1.0,
        "Evening Watch": 1.4,
        "Morning Watch": 0.7,

    }.get(time_of_day, 1.0)

    time_multiplier = location_time_multiplier * base_time_multiplier

    risk_score = min(math.log1p(weighted_score) * 4.04 * time_multiplier, 100)

    return round(risk_score, 2), total



def address_to_coords(address):
    geolocator = Nominatim(user_agent="atlanta_risk_app")
    location = geolocator.geocode(address)

    if location:
        return location.latitude, location.longitude
    else:
        return None, None


def geocode_addresses(df, street_col, city_col, state_col, user_agent="map_app"):

    geolocator = Nominatim(user_agent=user_agent)
    latitudes = []
    longitudes = []

    for _, row in df.iterrows():
        street_number = row.get(street_col, '')
        street = row.get(street_col.replace("NUMBER", ""), '')
        city = row.get(city_col, '')
        state = row.get(state_col, '')

        address = f"{street_number} {street}, {city}, {state}".strip(', ')

        try:
            location = geolocator.geocode(address)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
            else:
                latitudes.append(None)
                longitudes.append(None)
        except Exception as e:
            print(f"Geocoding failed for {address}: {e}")
            latitudes.append(None)
            longitudes.append(None)

        time.sleep(1)

    df['LATITUDE'] = latitudes
    df['LONGITUDE'] = longitudes
    return df



if __name__ == "__main__":

    address = "Georgia State University, Atlanta"
    lat, lon = address_to_coords(address)

    if lat:
        score, count = calculate_risk(lat, lon, "Evening Watch")
        print("Address:", address)
        print("Nearby crimes:", count)
        print("Risk score:", score)
    else:
        print("Address not found.")