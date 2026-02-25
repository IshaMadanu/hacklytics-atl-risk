from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import os
import sys
import requests
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
from risk_model import calculate_risk, address_to_coords, sexoffender_df

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# Load Sex Offender Data
# -----------------------------
so_df = sexoffender_df.copy()
so_df.columns = so_df.columns.str.strip()

print("Columns in CSV:", so_df.columns.tolist())

if "LATITUDE" in so_df.columns:
    so_df["LATITUDE"] = pd.to_numeric(so_df["LATITUDE"], errors="coerce")
if "LONGITUDE" in so_df.columns:
    so_df["LONGITUDE"] = pd.to_numeric(so_df["LONGITUDE"], errors="coerce")

print(so_df.head())

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    offenders = so_df.to_dict(orient="records")
    return render_template("index.html", offenders=offenders)


def hour_to_watch(hour):
    """Convert 24h hour to Atlanta PD watch string.
    Day Watch:     07:00 - 14:59
    Evening Watch: 15:00 - 22:59
    Morning Watch: 23:00 - 06:59
    """
    if 7 <= hour <= 14:
        return "Day Watch"
    elif 15 <= hour <= 22:
        return "Evening Watch"
    else:
        return "Morning Watch"

@app.route('/api/analyze', methods=['POST'])
def analyze():
    gemini_key = os.environ.get('GEMINI_API_KEY')
    data = request.get_json()

    response = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}',
        json=data
    )
    return jsonify(response.json()), response.status_code

@app.route("/risk")
def risk():
    address = request.args.get("address")
    time_of_day = request.args.get("time", "Evening Watch")

    hour = request.args.get("hour", type=int)
    if hour is not None:
        time_of_day = hour_to_watch(hour)

    if not address:
        return jsonify({"error": "Address required"}), 400

    lat, lon = address_to_coords(address)
    if lat is None or lon is None:
        return jsonify({"error": "Address not found"}), 404

    score, count = calculate_risk(lat, lon, time_of_day)

    return jsonify({
        "address": address,
        "latitude": lat,
        "longitude": lon,
        "risk_score": score,
        "nearby_crimes": count,
        "watch": time_of_day
    })


# Serve static resource data
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

@app.route('/chatanalyzer')
def chatanalyzer():
    return render_template('chatanalyzer.html')

if __name__ == "__main__":
    app.run(debug=True)