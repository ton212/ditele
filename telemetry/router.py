"""API router for telemetry endpoints."""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Vehicle, Position, Drive, ChargingSession, ChargingDataPoint
from telemetry.schemas import (
    TelemetryRequest,
    TelemetryResponse,
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleResponse,
    VehicleListResponse,
)
from telemetry.transformer import transform_telemetry_data
from telemetry.interpreter import map_gear_position
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
    
    # Note: updated_at is handled by SQLAlchemy onupdate
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
        
        # Transform raw data
        try:
            transformed = transform_telemetry_data(telemetry_data.model_dump())
        except Exception as e:
            logger.error(f"Error transforming telemetry data: {e}", exc_info=True)
            import traceback
            raise HTTPException(status_code=400, detail=f"Error processing telemetry data: {str(e)}\n{traceback.format_exc()}")
        
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
        from datetime import timezone
        timestamp = datetime.fromtimestamp(telemetry_data.timestamp / 1000.0, tz=timezone.utc)
        
        # Skip previous position query for now due to schema mismatch
        # TODO: Fix model to match actual database schema
        prev_position = None
        prev_gear = None  # Gear not stored in positions table
        current_gear = transformed.get("gear_position")
        
        # Check previous charging state from charging sessions
        prev_charging_session_result = await db.execute(
            select(ChargingSession)
            .where(ChargingSession.vehicle_id == vehicle_id)
            .where(ChargingSession.end_date.is_(None))
            .order_by(ChargingSession.start_date.desc())
            .limit(1)
        )
        prev_charging = prev_charging_session_result.scalar_one_or_none() is not None
        current_charging = transformed.get("is_charging")
        
        # Drive detection logic
        # Since gear_position is not stored in positions, we'll use a simple heuristic:
        # If speed > 0 and no active drive, start one. If speed == 0 and active drive, end it.
        # For now, we'll use gear from current telemetry to detect transitions
        active_drive = None
        drive_started = False
        
        # Simple drive detection: check if there's an active drive
        # Start drive if gear is D/N/R/S/M and no active drive exists
        # End drive if gear is P and active drive exists
        active_drive_result = await db.execute(
            select(Drive)
            .where(Drive.vehicle_id == vehicle_id)
            .where(Drive.end_date.is_(None))
            .order_by(Drive.start_date.desc())
            .limit(1)
        )
        existing_active_drive = active_drive_result.scalar_one_or_none()
        
        if current_gear in ["D", "N", "R", "S", "M"] and not existing_active_drive:
            # Drive start: gear is in drive mode and no active drive
            logger.info(f"Drive started for vehicle {vehicle_id}")
            drive_started = True
            active_drive = Drive(
                vehicle_id=vehicle_id,
                start_date=timestamp,
                start_km=transformed.get("odometer"),
                start_battery_range_km=transformed.get("battery_range_km"),
            )
            db.add(active_drive)
            await db.flush()  # Get the drive ID
            active_drive = active_drive  # Use the new drive
        
        elif current_gear == "P" and existing_active_drive:
            # Drive end: gear changed to Park
            logger.info(f"Drive ended for vehicle {vehicle_id}")
            ended_drive = existing_active_drive
            
            if ended_drive:
                ended_drive.end_date = timestamp
                ended_drive.end_km = transformed.get("odometer")
                ended_drive.end_battery_range_km = transformed.get("battery_range_km")
                
                # Calculate aggregates from positions in this drive using ORM
                positions_result = await db.execute(
                    select(Position)
                    .where(Position.drive_id == ended_drive.id)
                    .order_by(Position.timestamp.asc())
                )
                drive_positions = positions_result.scalars().all()
                
                if drive_positions:
                    speeds = [p.speed for p in drive_positions if p.speed is not None]
                    powers = [p.power for p in drive_positions if p.power is not None]
                    temps = [p.outside_temp for p in drive_positions if p.outside_temp is not None]
                    
                    if speeds:
                        ended_drive.speed_max = max(speeds)
                    if powers:
                        ended_drive.power_max = max(powers)
                        ended_drive.power_min = min(powers)
                        ended_drive.power_avg = int(sum(powers) / len(powers))
                    if temps:
                        ended_drive.outside_temp_avg = sum(temps) / len(temps)
                    
                    if ended_drive.start_km and ended_drive.end_km:
                        ended_drive.distance = float(ended_drive.end_km) - float(ended_drive.start_km)
                    
                    if ended_drive.start_date and ended_drive.end_date:
                        duration_seconds = (ended_drive.end_date - ended_drive.start_date).total_seconds()
                        ended_drive.duration_min = int(duration_seconds / 60)
                    
                    # Get first and last position IDs using ORM
                    if drive_positions:
                        ended_drive.start_position_id = drive_positions[0].id
                        ended_drive.end_position_id = drive_positions[-1].id
            
            # Drive has ended, so no active drive
            active_drive = None
        
        else:
            # Continue existing drive or no drive
            active_drive = existing_active_drive
        
        # Charging session logic
        active_charging_session = None
        charging_started = False
        
        if prev_charging is False and current_charging is True:
            # Charging start
            logger.info(f"Charging started for vehicle {vehicle_id}")
            charging_started = True
            active_charging_session = ChargingSession(
                vehicle_id=vehicle_id,
                start_date=timestamp,
                start_battery_level=transformed.get("battery_level"),
            )
            db.add(active_charging_session)
            await db.flush()
        
        elif prev_charging is True and current_charging is False:
            # Charging end
            logger.info(f"Charging ended for vehicle {vehicle_id}")
            active_session_result = await db.execute(
                select(ChargingSession)
                .where(ChargingSession.vehicle_id == vehicle_id)
                .where(ChargingSession.end_date.is_(None))
                .order_by(ChargingSession.start_date.desc())
                .limit(1)
            )
            active_charging_session = active_session_result.scalar_one_or_none()
            
            if active_charging_session:
                active_charging_session.end_date = timestamp
                active_charging_session.end_battery_level = transformed.get("battery_level")
                
                # Calculate duration
                if active_charging_session.start_date:
                    duration_seconds = (timestamp - active_charging_session.start_date).total_seconds()
                    active_charging_session.duration_min = int(duration_seconds / 60)
        
        else:
            # Check for active charging session
            active_session_result = await db.execute(
                select(ChargingSession)
                .where(ChargingSession.vehicle_id == vehicle_id)
                .where(ChargingSession.end_date.is_(None))
                .order_by(ChargingSession.start_date.desc())
                .limit(1)
            )
            active_charging_session = active_session_result.scalar_one_or_none()
        
        # Create charging data point if charging
        if active_charging_session and current_charging:
            charging_data_point = ChargingDataPoint(
                charging_session_id=active_charging_session.id,
                timestamp=timestamp,
                battery_level=transformed.get("battery_level"),
                charge_energy_added=transformed.get("charge_energy_added"),
                charger_power=transformed.get("charger_power"),
                outside_temp=transformed.get("outside_temp"),
            )
            db.add(charging_data_point)
        
        # Create position record using ORM
        # Note: latitude/longitude can be None for parked vehicles without GPS
        # If GPS is unavailable, use last known position or a default
        lat = transformed.get("latitude")
        lon = transformed.get("longitude")
        if lat is None or lon is None:
            # If no GPS, use last known position or skip this position
            # For now, we'll use a default location (0,0) - in production you'd handle this better
            lat = lat or 0.0
            lon = lon or 0.0
        
        # Create position using ORM
        position = Position(
            vehicle_id=vehicle_id,
            timestamp=timestamp,
            latitude=lat,
            longitude=lon,
            heading=transformed.get("heading"),
            gps_accuracy=transformed.get("gps_accuracy"),
            speed=transformed.get("speed"),
            odometer=transformed.get("odometer"),
            battery_level=transformed.get("battery_level"),
            battery_range_km=transformed.get("battery_range_km"),
            outside_temp=transformed.get("outside_temp"),
            inside_temp=transformed.get("inside_temp"),
            power=transformed.get("power"),
            is_climate_on=transformed.get("is_climate_on"),
            driver_temp_setting=transformed.get("driver_temp_setting"),
            passenger_temp_setting=transformed.get("passenger_temp_setting"),
            is_rear_defroster_on=transformed.get("is_rear_defroster_on"),
            is_front_defroster_on=transformed.get("is_front_defroster_on"),
            gear_position=transformed.get("gear_position"),
            fan_level=transformed.get("fan_level"),
            wind_mode=transformed.get("wind_mode"),
            cycle_mode=transformed.get("cycle_mode"),
            tire_pressure_fl=transformed.get("tire_pressure_fl"),
            tire_pressure_fr=transformed.get("tire_pressure_fr"),
            tire_pressure_rl=transformed.get("tire_pressure_rl"),
            tire_pressure_rr=transformed.get("tire_pressure_rr"),
            tire_temp_fl=transformed.get("tire_temp_fl"),
            tire_temp_fr=transformed.get("tire_temp_fr"),
            tire_temp_rl=transformed.get("tire_temp_rl"),
            tire_temp_rr=transformed.get("tire_temp_rr"),
            pm25_inside=transformed.get("pm25_inside"),
            pm25_outside=transformed.get("pm25_outside"),
            drive_id=active_drive.id if active_drive else None,
        )
        db.add(position)
        await db.flush()  # Flush to get the position ID
        position_id = position.id
        
        # Update drive start_position_id if this is the first position in a new drive
        if active_drive and drive_started:
            active_drive.start_position_id = position_id
        
        await db.commit()
        
        return TelemetryResponse(
            success=True,
            message="Telemetry data received successfully",
            position_id=position_id,
            drive_id=active_drive.id if active_drive else None,
            charging_session_id=active_charging_session.id if active_charging_session else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in telemetry endpoint: {e}", exc_info=True)
        await db.rollback()
        import traceback
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}\n{traceback.format_exc()}")

