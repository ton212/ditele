#!/usr/bin/env python3
"""Test script for the telemetry API."""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 5  # 5 second timeout for all requests

def test_vehicle_crud():
    """Test vehicle CRUD operations."""
    print("=== Testing Vehicle CRUD ===")
    
    # Create vehicle (or get existing)
    print("\n1. Creating vehicle...")
    import time
    vin = f"TEST{int(time.time())}"
    response = requests.post(
        f"{BASE_URL}/vehicles",
        json={"vin": vin, "model": "BYD Test Model"},
        timeout=TIMEOUT
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        vehicle = response.json()
        print(f"Created vehicle: {json.dumps(vehicle, indent=2, default=str)}")
        vehicle_id = vehicle["id"]
    elif response.status_code == 500 and "duplicate key" in response.text:
        # Vehicle exists, get it
        print("Vehicle already exists, fetching existing...")
        response = requests.get(f"{BASE_URL}/vehicles")
        if response.status_code == 200:
            vehicles = response.json()["vehicles"]
            if vehicles:
                vehicle_id = vehicles[0]["id"]
                print(f"Using existing vehicle ID: {vehicle_id}")
            else:
                print("Error: No vehicles found")
                return None
        else:
            print(f"Error: {response.text}")
            return None
    else:
        print(f"Error: {response.text}")
        return None
    
    # List vehicles
    print("\n2. Listing vehicles...")
    response = requests.get(f"{BASE_URL}/vehicles", timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} vehicles")
    
    # Get vehicle
    print(f"\n3. Getting vehicle {vehicle_id}...")
    response = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}", timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Vehicle: {json.dumps(response.json(), indent=2, default=str)}")
    
    # Update vehicle
    print(f"\n4. Updating vehicle {vehicle_id}...")
    response = requests.put(
        f"{BASE_URL}/vehicles/{vehicle_id}",
        json={"model": "BYD Updated Model"},
        timeout=TIMEOUT
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Updated vehicle: {json.dumps(response.json(), indent=2, default=str)}")
    
    return vehicle_id

def test_telemetry(vehicle_id):
    """Test telemetry endpoint."""
    print("\n=== Testing Telemetry Endpoint ===")
    
    # Load test data
    with open("test_telemetry.json", "r") as f:
        telemetry_data = json.load(f)
    
    # Update timestamp
    telemetry_data["timestamp"] = int(datetime.now().timestamp() * 1000)
    
    print(f"\n1. Sending telemetry data for vehicle {vehicle_id}...")
    response = requests.post(
        f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}",
        json=telemetry_data,
        timeout=TIMEOUT
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, default=str)}")
        return result
    else:
        print(f"Error: {response.text}")
        return None

def test_drive_detection(vehicle_id):
    """Test drive detection logic."""
    print("\n=== Testing Drive Detection ===")
    
    base_time = int(datetime.now().timestamp() * 1000)
    
    # Position 1: Park
    print("\n1. Position with gear P (Park)...")
    data1 = {
        "timestamp": base_time,
        "devices": {
            "BYDAutoGearboxDevice": {"getGearboxAutoModeType": 1},  # P
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
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data1, timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
    
    # Position 2: Drive (should start drive)
    print("\n2. Position with gear D (Drive) - should start drive...")
    data2 = {
        "timestamp": base_time + 10000,
        "devices": {
            "BYDAutoGearboxDevice": {"getGearboxAutoModeType": 4},  # D
            "BYDAutoSpeedDevice": {"getCurrentSpeed": 30},
            "BYDAutoStatisticDevice": {
                "getTotalMileageValue": 39411,
                "getSOCBatteryPercentage": 44,
                "getElecDrivingRangeValue": 183
            },
            "BYDAutoInstrumentDevice": {
                "getOutCarTemperature": 25,
                "getUnit(int)": {"1": 1, "2": 3, "4": 1}
            }
        },
        "location": {"latitude": 37.7750, "longitude": -122.4195}
    }
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data2, timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, default=str)}")
        drive_id = result.get("drive_id")
        if drive_id:
            print(f"✓ Drive started! Drive ID: {drive_id}")
    
    # Position 3: Park again (should end drive)
    print("\n3. Position with gear P (Park) again - should end drive...")
    data3 = {
        "timestamp": base_time + 20000,
        "devices": {
            "BYDAutoGearboxDevice": {"getGearboxAutoModeType": 1},  # P
            "BYDAutoSpeedDevice": {"getCurrentSpeed": 0},
            "BYDAutoStatisticDevice": {
                "getTotalMileageValue": 39412,
                "getSOCBatteryPercentage": 43,
                "getElecDrivingRangeValue": 182
            },
            "BYDAutoInstrumentDevice": {
                "getOutCarTemperature": 25,
                "getUnit(int)": {"1": 1, "2": 3, "4": 1}
            }
        },
        "location": {"latitude": 37.7751, "longitude": -122.4196}
    }
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data3, timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, default=str)}")
        if not result.get("drive_id"):
            print("✓ Drive ended!")

def test_unit_conversions(vehicle_id):
    """Test unit conversion."""
    print("\n=== Testing Unit Conversions ===")
    
    # Test with Fahrenheit and psi
    print("\nTesting with Fahrenheit (77F = 25C) and psi (57psi ≈ 3.93bar)...")
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
                "getOutCarTemperature": 77,  # 77F
                "getInCarTemperature": 72,   # 72F
                "getUnit(int)": {"1": 2, "2": 2, "4": 1},  # F, psi, kW
                "getWheelPressure(int)": {"1": 57, "2": 57, "3": 57, "4": 57},  # 57 psi
                "getWheelTemperature(int)": {"1": 84, "2": 81, "3": 84, "4": 81}  # 84F, 81F
            },
            "BYDAutoChargingDevice": {"getChargingPower": 0}
        },
        "location": {"latitude": 37.7749, "longitude": -122.4194}
    }
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data, timeout=TIMEOUT)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        print("\n✓ Unit conversion test completed")
        print("Expected: outside_temp ≈ 25°C, tire_pressure ≈ 3.93 bar")

if __name__ == "__main__":
    print("Starting API tests...\n")
    
    # Test vehicle CRUD
    vehicle_id = test_vehicle_crud()
    
    if vehicle_id:
        # Test telemetry
        test_telemetry(vehicle_id)
        
        # Test drive detection
        test_drive_detection(vehicle_id)
        
        # Test unit conversions
        test_unit_conversions(vehicle_id)
        
        print("\n=== All tests completed! ===")
    else:
        print("\n✗ Failed to create vehicle, skipping other tests")

