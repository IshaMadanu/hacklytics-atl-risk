# geocode_sexoffenders_atlanta.py

import pandas as pd
from geopy.geocoders import Nominatim
import time
import os

# -----------------------------
# 1️⃣ Load CSV
# -----------------------------
input_file = r"C:\Users\aliso\OneDrive\Documents\Hack\Hacklytics2026\hacklytics2026\sexoffender.csv"
output_file = r"C:\Users\aliso\OneDrive\Documents\Hack\Hacklytics2026\hacklytics2026\sexoffender_geocoded.csv"

df = pd.read_csv(input_file, encoding="utf-8-sig")

# -----------------------------
# 2️⃣ Filter Atlanta ZIP codes
# -----------------------------
atl_zips = [
    '30303','30308','30310','30312','30313','30314','30315','30316',
    '30318','30319','30324','30326','30327','30328','30329','30331',
    '30332','30334','30336','30337','30338','30339','30340','30341',
    '30342','30344','30349','30350','30354'
]

df = df[df['ZIP CODE'].astype(str).isin(atl_zips)].reset_index(drop=True)
print(f"Rows to geocode (Atlanta only): {len(df)}")

# -----------------------------
# 3️⃣ Setup geolocator
# -----------------------------
geolocator = Nominatim(user_agent="atl_offender_map")

# Add Latitude/Longitude columns if missing
if 'Latitude' not in df.columns:
    df['Latitude'] = None
if 'Longitude' not in df.columns:
    df['Longitude'] = None

# -----------------------------
# 4️⃣ Geocode missing entries
# -----------------------------
for i, row in df.iterrows():
    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
        continue  # Already geocoded

    address = f"{row['STREET NUMBER']} {row['STREET']}, {row['CITY']}, {row['STATE']}"
    try:
        location = geolocator.geocode(address)
        if location:
            df.at[i, 'Latitude'] = location.latitude
            df.at[i, 'Longitude'] = location.longitude
            print(f"[{i}] Geocoded {row['NAME']} → {location.latitude},{location.longitude}")
        else:
            print(f"[{i}] Could not geocode {row['NAME']}")
    except Exception as e:
        print(f"[{i}] Error geocoding {row['NAME']}: {e}")

    time.sleep(1)  # Nominatim rate limit

    # -----------------------------
    # Save progress every 5 rows
    # -----------------------------
    if i % 5 == 0:
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"Progress saved at row {i}")

# -----------------------------
# 5️⃣ Final save
# -----------------------------
df.rename(columns={'NAME': 'sor', 'LEVELING': 'Level'}, inplace=True)
df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"Geocoding finished. CSV saved as {output_file}")