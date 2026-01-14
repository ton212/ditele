"""Test that verifies data is actually stored correctly in the database."""
import json
import requests
import time
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from database.connection import AsyncSessionLocal
from database.models import Vehicle, Position, Drive, ChargingSession

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 5


async def verify_position_in_db(db: AsyncSession, position_id: int, expected_data: dict):
    """Verify that a position record exists in the database with correct data."""
        result = await db.execute(select(Position).where(Position.id == position_id))
        position = result.scalar_one_or_none()
        
        if not position:
            return False, "Position not found in database"
        
        errors = []
        
        # Verify basic fields
        if position.vehicle_id != expected_data.get("vehicle_id"):
            errors.append(f"vehicle_id: expected {expected_data.get('vehicle_id')}, got {position.vehicle_id}")
        
        if position.speed != expected_data.get("speed"):
            errors.append(f"speed: expected {expected_data.get('speed')}, got {position.speed}")
        
        if position.battery_level != expected_data.get("battery_level"):
            errors.append(f"battery_level: expected {expected_data.get('battery_level')}, got {position.battery_level}")
        
        if position.odometer != expected_data.get("odometer"):
            errors.append(f"odometer: expected {expected_data.get('odometer')}, got {position.odometer}")
        
        # Verify GPS (with tolerance for float comparison)
        if expected_data.get("latitude") is not None:
            if abs(float(position.latitude or 0) - float(expected_data.get("latitude", 0))) > 0.0001:
                errors.append(f"latitude: expected {expected_data.get('latitude')}, got {position.latitude}")
        
        if expected_data.get("longitude") is not None:
            if abs(float(position.longitude or 0) - float(expected_data.get("longitude", 0))) > 0.0001:
                errors.append(f"longitude: expected {expected_data.get('longitude')}, got {position.longitude}")
        
        # Verify temperatures (with tolerance)
        if expected_data.get("outside_temp") is not None:
            if abs(float(position.outside_temp or 0) - float(expected_data.get("outside_temp", 0))) > 0.1:
                errors.append(f"outside_temp: expected {expected_data.get('outside_temp')}, got {position.outside_temp}")
        
        if expected_data.get("inside_temp") is not None:
            if abs(float(position.inside_temp or 0) - float(expected_data.get("inside_temp", 0))) > 0.1:
                errors.append(f"inside_temp: expected {expected_data.get('inside_temp')}, got {position.inside_temp}")
        
        # Verify tire pressures
        if expected_data.get("tire_pressure_fl") is not None:
            if abs(float(position.tire_pressure_fl or 0) - float(expected_data.get("tire_pressure_fl", 0))) > 0.1:
                errors.append(f"tire_pressure_fl: expected {expected_data.get('tire_pressure_fl')}, got {position.tire_pressure_fl}")
        
        # Verify tire temperatures
        if expected_data.get("tire_temp_fl") is not None:
            if abs(float(position.tire_temp_fl or 0) - float(expected_data.get("tire_temp_fl", 0))) > 0.1:
                errors.append(f"tire_temp_fl: expected {expected_data.get('tire_temp_fl')}, got {position.tire_temp_fl}")
        
        # Verify AC settings
        if expected_data.get("driver_temp_setting") is not None:
            if abs(float(position.driver_temp_setting or 0) - float(expected_data.get("driver_temp_setting", 0))) > 0.1:
                errors.append(f"driver_temp_setting: expected {expected_data.get('driver_temp_setting')}, got {position.driver_temp_setting}")
        
        if expected_data.get("passenger_temp_setting") is not None:
            if abs(float(position.passenger_temp_setting or 0) - float(expected_data.get("passenger_temp_setting", 0))) > 0.1:
                errors.append(f"passenger_temp_setting: expected {expected_data.get('passenger_temp_setting')}, got {position.passenger_temp_setting}")
        
        if position.wind_mode != expected_data.get("wind_mode"):
            errors.append(f"wind_mode: expected {expected_data.get('wind_mode')}, got {position.wind_mode}")
        
        if position.gear_position != expected_data.get("gear_position"):
            errors.append(f"gear_position: expected {expected_data.get('gear_position')}, got {position.gear_position}")
        
        if position.is_climate_on != expected_data.get("is_climate_on"):
            errors.append(f"is_climate_on: expected {expected_data.get('is_climate_on')}, got {position.is_climate_on}")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "All fields match"


async def verify_drive_in_db(db: AsyncSession, drive_id: int, expected_vehicle_id: int):
    """Verify that a drive record exists and is linked correctly."""
        result = await db.execute(select(Drive).where(Drive.id == drive_id))
        drive = result.scalar_one_or_none()
        
        if not drive:
            return False, "Drive not found in database"
        
        if drive.vehicle_id != expected_vehicle_id:
            return False, f"Drive vehicle_id mismatch: expected {expected_vehicle_id}, got {drive.vehicle_id}"
        
        return True, "Drive verified"


def test_with_sample_data():
    """Test with the actual sample data file and verify in database."""
    print("\n" + "=" * 60)
    print("DATABASE VERIFICATION TEST")
    print("=" * 60)
    
    # Load sample data
    print("\n1. Loading sample data...")
    with open('../docs/flattened_data_sample.json', 'r') as f:
        sample_data = json.load(f)
    
    # Create vehicle
    print("2. Creating test vehicle...")
    create_resp = requests.post(
        f"{BASE_URL}/vehicles",
        json={"vin": f"TEST_DB_VERIFY_{int(time.time())}", "model": "BYD Test"},
        timeout=TIMEOUT
    )
    if create_resp.status_code != 201:
        print(f"✗ Failed to create vehicle: {create_resp.status_code}")
        return False
    vehicle_id = create_resp.json()["id"]
    print(f"   ✓ Created vehicle ID: {vehicle_id}")
    
    # Update timestamp
    sample_data["timestamp"] = int(time.time() * 1000)
    
    # Calculate expected values
    from telemetry.transformer import transform_telemetry_data
    transformed = transform_telemetry_data(sample_data)
    
    print("\n3. Sending telemetry data...")
    response = requests.post(
        f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}",
        json=sample_data,
        timeout=TIMEOUT
    )
    
    if response.status_code != 200:
        print(f"✗ API call failed: {response.status_code}")
        print(response.text[:500])
        return False
    
    result = response.json()
    position_id = result.get("position_id")
    print(f"   ✓ API returned position_id: {position_id}")
    
    # Verify in database
    print("\n4. Verifying data in database...")
    expected_data = {
        "vehicle_id": vehicle_id,
        "speed": transformed.get("speed"),
        "battery_level": transformed.get("battery_level"),
        "odometer": transformed.get("odometer"),
        "latitude": transformed.get("latitude"),
        "longitude": transformed.get("longitude"),
        "outside_temp": transformed.get("outside_temp"),
        "inside_temp": transformed.get("inside_temp"),
        "tire_pressure_fl": transformed.get("tire_pressure_fl"),
        "tire_temp_fl": transformed.get("tire_temp_fl"),
        "driver_temp_setting": transformed.get("driver_temp_setting"),
        "passenger_temp_setting": transformed.get("passenger_temp_setting"),
        "wind_mode": transformed.get("wind_mode"),
        "gear_position": transformed.get("gear_position"),
        "is_climate_on": transformed.get("is_climate_on"),
    }
    
    success, message = asyncio.run(verify_position_in_db(position_id, expected_data))
    
    if success:
        print(f"   ✓ Database verification passed!")
        print(f"   ✓ All fields match expected values")
    else:
        print(f"   ✗ Database verification failed: {message}")
        return False
    
    # Test drive detection
    print("\n5. Testing drive detection with database verification...")
    
    # Position 1: Park
    park_data = sample_data.copy()
    park_data["timestamp"] = int(time.time() * 1000) + 1000
    park_data["devices"]["BYDAutoGearboxDevice"]["getGearboxAutoModeType"] = 1  # P
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=park_data, timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["drive_id"] is None
    
    # Position 2: Drive (should start drive)
    drive_data = sample_data.copy()
    drive_data["timestamp"] = int(time.time() * 1000) + 2000
    drive_data["devices"]["BYDAutoGearboxDevice"]["getGearboxAutoModeType"] = 4  # D
    drive_data["devices"]["BYDAutoSpeedDevice"]["getCurrentSpeed"] = 50
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=drive_data, timeout=TIMEOUT)
    assert response.status_code == 200
    drive_id = response.json()["drive_id"]
    assert drive_id is not None, "Drive should have started"
    print(f"   ✓ Drive started with ID: {drive_id}")
    
    # Verify drive in database
    success, message = asyncio.run(verify_drive_in_db(drive_id, vehicle_id))
    if success:
        print(f"   ✓ Drive verified in database")
    else:
        print(f"   ✗ Drive verification failed: {message}")
        return False
    
    # Position 3: Park again (should end drive)
    park_data2 = sample_data.copy()
    park_data2["timestamp"] = int(time.time() * 1000) + 3000
    park_data2["devices"]["BYDAutoGearboxDevice"]["getGearboxAutoModeType"] = 1  # P
    response = requests.post(f"{BASE_URL}/telemetry?vehicle_id={vehicle_id}", json=park_data2, timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["drive_id"] is None, "Drive should have ended"
    print(f"   ✓ Drive ended")
    
    # Verify drive was updated in database
    async def verify_drive_ended():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Drive).where(Drive.id == drive_id))
            drive = result.scalar_one_or_none()
            if not drive:
                return False, "Drive not found"
            if drive.end_date is None:
                return False, "Drive end_date is None"
            if drive.distance is None:
                return False, "Drive distance is None"
            return True, "Drive properly ended"
    
    success, message = asyncio.run(verify_drive_ended())
    if success:
        print(f"   ✓ Drive end verified in database")
    else:
        print(f"   ✗ Drive end verification failed: {message}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL DATABASE VERIFICATION TESTS PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_with_sample_data()

