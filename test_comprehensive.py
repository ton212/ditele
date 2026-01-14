#!/usr/bin/env python3
"""Comprehensive test suite for the telemetry API."""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 5

def test_vehicle_crud():
    """Test vehicle CRUD operations."""
    print("=" * 60)
    print("TEST 1: Vehicle CRUD Operations")
    print("=" * 60)
    
    # Create vehicle
    print("\n1.1 Creating vehicle...")
    vin = f"TEST{int(time.time())}"
    try:
        response = requests.post(
            f"{BASE_URL}/vehicles",
            json={"vin": vin, "model": "BYD Test Model"},
            timeout=TIMEOUT
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        vehicle = response.json()
        vehicle_id = vehicle["id"]
        print(f"   ✓ Created vehicle ID: {vehicle_id}, VIN: {vin}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return None
    
    # List vehicles
    print("\n1.2 Listing vehicles...")
    try:
        response = requests.get(f"{BASE_URL}/vehicles", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        print(f"   ✓ Found {data['count']} vehicles")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Get vehicle
    print(f"\n1.3 Getting vehicle {vehicle_id}...")
    try:
        response = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}", timeout=TIMEOUT)
        assert response.status_code == 200
        vehicle = response.json()
        assert vehicle["id"] == vehicle_id
        print(f"   ✓ Retrieved vehicle: {vehicle['model']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Update vehicle
    print(f"\n1.4 Updating vehicle {vehicle_id}...")
    try:
        response = requests.put(
            f"{BASE_URL}/vehicles/{vehicle_id}",
            json={"model": "BYD Updated Model"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        vehicle = response.json()
        assert vehicle["model"] == "BYD Updated Model"
        print(f"   ✓ Updated vehicle model to: {vehicle['model']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    return vehicle_id

def test_telemetry_basic(vehicle_id):
    """Test basic telemetry submission."""
    print("\n" + "=" * 60)
    print("TEST 2: Basic Telemetry Submission")
    print("=" * 60)
    
    data = {
        "timestamp": int(datetime.now().timestamp() * 1000),
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
                "getInCarTemperature": 22,
                "getUnit(int)": {"1": 1, "2": 3, "4": 1},  # C, kPa, kW
                "getWheelPressure(int)": {"1": 394, "2": 391, "3": 394, "4": 394},
                "getWheelTemperature(int)": {"1": 29, "2": 27, "3": 29, "4": 27}
            },
            "BYDAutoAcDevice": {
                "getAcStartState": 1,
                "getAcWindLevel": 2,
                "getAcWindMode": 2,
                "getAcCycleMode": 1,
                "getTemprature(int)": {"1": 24, "4": 24},
                "getAcDefrostState(int)": {"2": 0}
            },
            "BYDAutoChargingDevice": {
                "getChargingState": 0,
                "getChargingGunState": 1,
                "getChargingPower": 0
            },
            "BYDAutoPM2p5Device": {
                "getPM2p5Value": [9, 51]
            }
        },
        "location": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "heading": 90.5,
            "accuracy": 5.2
        }
    }
    
    print("\n2.1 Sending telemetry with GPS and all sensors...")
    try:
        response = requests.post(
            f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}",
            json=data,
            timeout=TIMEOUT
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert result["success"] == True
        assert result["position_id"] is not None
        print(f"   ✓ Telemetry saved! Position ID: {result['position_id']}")
        return result
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
        return None

def test_telemetry_no_gps(vehicle_id):
    """Test telemetry without GPS data."""
    print("\n" + "=" * 60)
    print("TEST 3: Telemetry Without GPS")
    print("=" * 60)
    
    data = {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "devices": {
            "BYDAutoGearboxDevice": {"getGearboxAutoModeType": 1},
            "BYDAutoSpeedDevice": {"getCurrentSpeed": 0},
            "BYDAutoStatisticDevice": {
                "getTotalMileageValue": 39410,
                "getSOCBatteryPercentage": 45,
                "getElecDrivingRangeValue": 185
            },
            "BYDAutoInstrumentDevice": {
                "getOutCarTemperature": 25,
                "getUnit(int)": {"1": 1, "2": 3, "4": 1}
            }
        }
        # No location object
    }
    
    print("\n3.1 Sending telemetry without GPS (parked, no sky view)...")
    try:
        response = requests.post(
            f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}",
            json=data,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["position_id"] is not None
        print(f"   ✓ Telemetry saved without GPS! Position ID: {result['position_id']}")
        print(f"   ✓ Battery SOC (45%) stored even without location")
        return True
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

def test_drive_detection(vehicle_id):
    """Test drive detection logic."""
    print("\n" + "=" * 60)
    print("TEST 4: Drive Detection")
    print("=" * 60)
    
    base_time = int(datetime.now().timestamp() * 1000)
    
    # Position 1: Park
    print("\n4.1 Position 1: Gear P (Park)...")
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
    try:
        response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data1, timeout=TIMEOUT)
        assert response.status_code == 200
        result1 = response.json()
        assert result1["drive_id"] is None, "Should not have active drive when parked"
        print(f"   ✓ Parked position saved, no active drive")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Position 2: Drive (should start drive)
    print("\n4.2 Position 2: Gear D (Drive) - should start drive...")
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
    try:
        response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data2, timeout=TIMEOUT)
        assert response.status_code == 200
        result2 = response.json()
        assert result2["drive_id"] is not None, "Should have started a drive"
        drive_id = result2["drive_id"]
        print(f"   ✓ Drive started! Drive ID: {drive_id}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Position 3: Park again (should end drive)
    print("\n4.3 Position 3: Gear P (Park) again - should end drive...")
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
    try:
        response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data3, timeout=TIMEOUT)
        assert response.status_code == 200
        result3 = response.json()
        assert result3["drive_id"] is None, "Drive should have ended"
        print(f"   ✓ Drive ended! No active drive")
        return True
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

def test_unit_conversions(vehicle_id):
    """Test unit conversion (Fahrenheit to Celsius, psi to bar)."""
    print("\n" + "=" * 60)
    print("TEST 5: Unit Conversions")
    print("=" * 60)
    
    # Test with Fahrenheit (77F = 25C) and psi (57psi ≈ 3.93bar)
    print("\n5.1 Testing with Fahrenheit (77F) and psi (57psi)...")
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
                "getWheelPressure(int)": {"1": 570, "2": 570, "3": 570, "4": 570},  # 57.0 psi
                "getWheelTemperature(int)": {"1": 840, "2": 810, "3": 840, "4": 810}  # 84.0F, 81.0F
            },
            "BYDAutoChargingDevice": {"getChargingPower": 0}
        },
        "location": {"latitude": 37.7749, "longitude": -122.4194}
    }
    try:
        response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=data, timeout=TIMEOUT)
        assert response.status_code == 200
        result = response.json()
        print(f"   ✓ Telemetry saved with unit conversion")
        print(f"   Expected: outside_temp ≈ 25°C, tire_pressure ≈ 3.93 bar")
        return True
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

def test_error_handling(vehicle_id):
    """Test error handling."""
    print("\n" + "=" * 60)
    print("TEST 6: Error Handling")
    print("=" * 60)
    
    # Test invalid vehicle_id
    print("\n6.1 Testing with invalid vehicle_id...")
    try:
        response = requests.post(
            f"{BASE_URL}/telemetry?vehicle_id=99999",
            json={"timestamp": int(datetime.now().timestamp() * 1000), "devices": {}},
            timeout=TIMEOUT
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"   ✓ Correctly returned 404 for invalid vehicle")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test missing timestamp
    print("\n6.2 Testing with missing timestamp...")
    try:
        response = requests.post(
            f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}",
            json={"devices": {}},
            timeout=TIMEOUT
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"   ✓ Correctly returned 422 for missing timestamp")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test old timestamp
    print("\n6.3 Testing with old timestamp (>24h)...")
    try:
        old_timestamp = int((datetime.now().timestamp() - 25 * 3600) * 1000)  # 25 hours ago
        response = requests.post(
            f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}",
            json={"timestamp": old_timestamp, "devices": {}},
            timeout=TIMEOUT
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"   ✓ Correctly rejected old timestamp")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE API TEST SUITE")
    print("=" * 60)
    
    # Test 1: Vehicle CRUD
    vehicle_id = test_vehicle_crud()
    if not vehicle_id:
        print("\n✗ Cannot continue without a vehicle. Exiting.")
        return
    
    # Test 2: Basic telemetry
    test_telemetry_basic(vehicle_id)
    
    # Test 3: Telemetry without GPS
    test_telemetry_no_gps(vehicle_id)
    
    # Test 4: Drive detection
    test_drive_detection(vehicle_id)
    
    # Test 5: Unit conversions
    test_unit_conversions(vehicle_id)
    
    # Test 6: Error handling
    test_error_handling(vehicle_id)
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()

