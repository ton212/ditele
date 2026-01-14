#!/usr/bin/env python3
"""Simple test for telemetry endpoint."""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 5  # 5 second timeout for all requests

# Get or create vehicle
try:
    response = requests.get(f"{BASE_URL}/vehicles", timeout=TIMEOUT)
    vehicles = response.json().get("vehicles", [])
    if vehicles:
        vehicle_id = vehicles[0]["id"]
    else:
        response = requests.post(f"{BASE_URL}/vehicles", json={"vin": "TEST", "model": "Test"}, timeout=TIMEOUT)
        vehicle_id = response.json()["id"]
except requests.exceptions.Timeout:
    print("ERROR: Request timed out")
    exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR: Request failed: {e}")
    exit(1)

print(f"Using vehicle ID: {vehicle_id}")

# Simple telemetry test
data = {
    "timestamp": int(datetime.now().timestamp() * 1000),
    "devices": {
        "BYDAutoGearboxDevice": {"getGearboxAutoModeType": 1},
        "BYDAutoSpeedDevice": {"getCurrentSpeed": 0},
        "BYDAutoStatisticDevice": {
            "getTotalMileageValue": 39410,
            "getSOCBatteryPercentage": 44,
            "getElecDrivingRangeValue": 184
        },
        "BYDAutoInstrumentDevice": {
            "getOutCarTemperature": 25,
            "getUnit(int)": {"1": 1, "2": 3, "4": 1}
        }
    },
    "location": {"latitude": 37.7749, "longitude": -122.4194}
}

try:
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data, timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out")
    exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR: Request failed: {e}")
    exit(1)

