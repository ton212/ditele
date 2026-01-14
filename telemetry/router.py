"""API router for telemetry endpoints."""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Vehicle, Position, Drive, ChargingSession
from telemetry.schemas import (
    TelemetryRequest,
    TelemetryResponse,
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleResponse,
    VehicleListResponse,
)
from telemetry.services import process_telemetry_data
from telemetry.transformer import transform_telemetry_data
from utils.validators import (
    validate_timestamp,
    validate_gps_coordinates,
    validate_heading,
    validate_gps_accuracy,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


# Vehicle CRUD endpoints

@router.get("/vehicles", response_model=VehicleListResponse)
async def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all vehicles."""
    result = await db.execute(
        select(Vehicle).offset(skip).limit(limit).order_by(Vehicle.id)
    )
    vehicles = result.scalars().all()
    
    count_result = await db.execute(select(func.count(Vehicle.id)))
    total_count = count_result.scalar()
    
    return VehicleListResponse(
        vehicles=[VehicleResponse.model_validate(v) for v in vehicles],
        count=total_count,
    )


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single vehicle by ID."""
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return VehicleResponse.model_validate(vehicle)


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    vehicle_data: VehicleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new vehicle."""
    try:
        vehicle = Vehicle(
            vin=vehicle_data.vin,
            model=vehicle_data.model,
        )
        db.add(vehicle)
        await db.commit()
        await db.refresh(vehicle)
        
        return VehicleResponse.model_validate(vehicle)
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating vehicle: {str(e)}")


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    vehicle_data: VehicleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a vehicle."""
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if vehicle_data.vin is not None:
        vehicle.vin = vehicle_data.vin
    if vehicle_data.model is not None:
        vehicle.model = vehicle_data.model
    
    await db.commit()
    await db.refresh(vehicle)
    
    return VehicleResponse.model_validate(vehicle)


@router.delete("/vehicles/{vehicle_id}", status_code=204)
async def delete_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a vehicle."""
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    await db.delete(vehicle)
    await db.commit()
    
    return None


# Telemetry endpoint

@router.post("/telemetry", response_model=TelemetryResponse)
async def receive_telemetry(
    vehicle_id: int = Query(..., description="Vehicle ID"),
    telemetry_data: TelemetryRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """Receive telemetry data from the agent.
    
    Args:
        vehicle_id: Vehicle ID from query parameter
        telemetry_data: Telemetry data payload
    
    Returns:
        Success response with position_id and any active drive/charging session IDs
    """
    try:
        # Validate vehicle exists
        vehicle_result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
        vehicle = vehicle_result.scalar_one_or_none()
        
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle with ID {vehicle_id} not found")
        
        # Validate timestamp
        if not validate_timestamp(telemetry_data.timestamp):
            raise HTTPException(status_code=400, detail="Invalid timestamp (too old or in future)")
        
        # Transform and validate data
        try:
            transformed = transform_telemetry_data(telemetry_data.model_dump())
        except Exception as e:
            logger.error(f"Error transforming telemetry data: {e}", exc_info=True)
            import traceback
            raise HTTPException(
                status_code=400,
                detail=f"Error processing telemetry data: {str(e)}\n{traceback.format_exc()}"
            )
        
        # Validate GPS coordinates if present
        if transformed.get("latitude") is not None or transformed.get("longitude") is not None:
            if not validate_gps_coordinates(transformed.get("latitude"), transformed.get("longitude")):
                raise HTTPException(status_code=400, detail="Invalid GPS coordinates")
        
        # Validate other fields
        if transformed.get("heading") is not None and not validate_heading(transformed["heading"]):
            raise HTTPException(status_code=400, detail="Invalid heading (must be 0-360)")
        
        if transformed.get("gps_accuracy") is not None and not validate_gps_accuracy(transformed["gps_accuracy"]):
            raise HTTPException(status_code=400, detail="Invalid GPS accuracy")
        
        # Convert timestamp from milliseconds to datetime (timezone-aware)
        timestamp = datetime.fromtimestamp(telemetry_data.timestamp / 1000.0, tz=timezone.utc)
        
        # Process telemetry data (business logic)
        position, active_drive, active_charging_session = await process_telemetry_data(
            db=db,
            vehicle_id=vehicle_id,
            telemetry_data=telemetry_data.model_dump(),
            timestamp=timestamp,
        )
        
        await db.commit()
        
        return TelemetryResponse(
            success=True,
            message="Telemetry data received successfully",
            position_id=position.id,
            drive_id=active_drive.id if active_drive else None,
            charging_session_id=active_charging_session.id if active_charging_session else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in telemetry endpoint: {e}", exc_info=True)
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}\n{traceback.format_exc()}"
        )
