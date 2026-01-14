"""Pydantic schemas for telemetry API."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class LocationData(BaseModel):
    """GPS location data from Android Location API."""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude in degrees")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude in degrees")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Bearing in degrees (0-360)")
    accuracy: Optional[float] = Field(None, ge=0, description="Horizontal accuracy in meters")


class TelemetryRequest(BaseModel):
    """Request schema for telemetry data.
    
    Supported BYD devices:
    - BYDAutoSpeedDevice: Vehicle speed data
    - BYDAutoStatisticDevice: Battery, odometer, and range data
    - BYDAutoGearboxDevice: Gear position data
    - BYDAutoInstrumentDevice: Temperature, tire pressure/temperature, and unit settings
    - BYDAutoAcDevice: Air conditioning settings and state
    - BYDAutoChargingDevice: Charging state and power
    - BYDAutoPM2p5Device: Air quality sensors (PM2.5)
    """
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    processId: Optional[int] = Field(None, description="Process ID")
    devices: Dict[str, Any] = Field(
        ...,
        description="Device data from BYD SDK. Supported devices: "
        "BYDAutoSpeedDevice, BYDAutoStatisticDevice, BYDAutoGearboxDevice, "
        "BYDAutoInstrumentDevice, BYDAutoAcDevice, BYDAutoChargingDevice, BYDAutoPM2p5Device",
        json_schema_extra={
            "example": {
                "BYDAutoSpeedDevice": {
                    "getCurrentSpeed": 0
                },
                "BYDAutoStatisticDevice": {
                    "getTotalMileageValue": 39410,
                    "getSOCBatteryPercentage": 44,
                    "getElecDrivingRangeValue": 184
                },
                "BYDAutoGearboxDevice": {
                    "getGearboxAutoModeType": 1
                },
                "BYDAutoInstrumentDevice": {
                    "getOutCarTemperature": 25,
                    "getInCarTemperature": 22,
                    "getUnit(int)": {
                        "1": 1,  # Temperature unit: 1=Celsius, 2=Fahrenheit
                        "2": 3,  # Pressure unit: 1=bar, 2=psi, 3=kPa
                        "4": 1   # Power unit: 1=kW, 2=HP
                    },
                    "getWheelPressure(int)": {
                        "1": 394,  # Front Left (value/10 = actual pressure)
                        "2": 391,  # Front Right
                        "3": 394,  # Rear Left
                        "4": 394   # Rear Right
                    },
                    "getWheelTemperature(int)": {
                        "1": 29,  # Front Left (°C)
                        "2": 27,  # Front Right
                        "3": 29,  # Rear Left
                        "4": 27   # Rear Right
                    }
                },
                "BYDAutoAcDevice": {
                    "getAcStartState": 1,
                    "getAcWindLevel": 2,
                    "getAcWindMode": 2,
                    "getAcCycleMode": 1,
                    "getTemprature(int)": {
                        "1": 25,  # Driver temperature
                        "4": 28   # Passenger temperature
                    },
                    "getAcDefrostState(int)": {
                        "2": 0  # Rear defroster
                    }
                },
                "BYDAutoChargingDevice": {
                    "getChargingState": 0,
                    "getChargingGunState": 1,
                    "getChargingPower": 0
                },
                "BYDAutoPM2p5Device": {
                    "getPM2p5Value": [9, 51]  # [inside, outside]
                }
            }
        }
    )
    location: Optional[LocationData] = Field(None, description="GPS location data (optional)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "description": "Telemetry data from BYD vehicle. All device data is optional, "
            "but at least one device should be provided for meaningful data collection."
        }
    )


class TelemetryResponse(BaseModel):
    """Response schema for telemetry endpoint."""
    success: bool = True
    message: str = "Telemetry data received successfully"
    position_id: Optional[int] = Field(None, description="ID of created position record")
    drive_id: Optional[int] = Field(None, description="ID of active drive (if any)")
    charging_session_id: Optional[int] = Field(None, description="ID of active charging session (if any)")


class VehicleCreateRequest(BaseModel):
    """Request schema for creating a vehicle."""
    vin: Optional[str] = Field(None, max_length=50, description="Vehicle Identification Number")
    model: Optional[str] = Field(None, max_length=100, description="Vehicle model")


class VehicleUpdateRequest(BaseModel):
    """Request schema for updating a vehicle."""
    vin: Optional[str] = Field(None, max_length=50, description="Vehicle Identification Number")
    model: Optional[str] = Field(None, max_length=100, description="Vehicle model")


class VehicleResponse(BaseModel):
    """Response schema for vehicle data."""
    id: int
    vin: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VehicleListResponse(BaseModel):
    """Response schema for vehicle list."""
    vehicles: List[VehicleResponse]
    count: int
