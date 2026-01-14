"""Pydantic schemas for telemetry API."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class LocationData(BaseModel):
    """GPS location data from Android Location API."""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude in degrees")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude in degrees")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Bearing in degrees (0-360)")
    accuracy: Optional[float] = Field(None, ge=0, description="Horizontal accuracy in meters")


class TelemetryRequest(BaseModel):
    """Request schema for telemetry data."""
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    processId: Optional[int] = Field(None, description="Process ID")
    devices: Dict[str, Any] = Field(..., description="Device data from BYD SDK")
    location: Optional[LocationData] = Field(None, description="GPS location data (optional)")
    
    # Timestamp validation is done in the router to return proper HTTP status codes
    # (400 instead of 422 for validation errors)


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
    
    class Config:
        from_attributes = True


class VehicleListResponse(BaseModel):
    """Response schema for vehicle list."""
    vehicles: List[VehicleResponse]
    count: int

