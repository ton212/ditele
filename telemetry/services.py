"""Business logic services for telemetry processing."""
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Vehicle, Position, Drive, ChargingSession, ChargingDataPoint
from telemetry.transformer import transform_telemetry_data

logger = logging.getLogger(__name__)


async def process_telemetry_data(
    db: AsyncSession,
    vehicle_id: int,
    telemetry_data: dict,
    timestamp: datetime,
) -> Tuple[Position, Optional[Drive], Optional[ChargingSession]]:
    """Process telemetry data and create/update database records.
    
    Args:
        db: Database session
        vehicle_id: Vehicle ID
        telemetry_data: Raw telemetry data dictionary
        timestamp: Parsed timestamp (timezone-aware)
    
    Returns:
        Tuple of (position, active_drive, active_charging_session)
    """
    # Transform raw data
    transformed = transform_telemetry_data(telemetry_data)
    
    # Get current gear for drive detection
    current_gear = transformed.get("gear_position")
    current_charging = transformed.get("is_charging")
    
    # Check for existing active drive
    active_drive_result = await db.execute(
        select(Drive)
        .where(Drive.vehicle_id == vehicle_id)
        .where(Drive.end_date.is_(None))
        .order_by(Drive.start_date.desc())
        .limit(1)
    )
    existing_active_drive = active_drive_result.scalar_one_or_none()
    
    # Handle drive detection
    active_drive, drive_started = await _handle_drive_detection(
        db, vehicle_id, timestamp, transformed, current_gear, existing_active_drive
    )
    
    # Handle charging session
    active_charging_session = await _handle_charging_session(
        db, vehicle_id, timestamp, transformed, current_charging
    )
    
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
    
    # Create position record
    position = _create_position(vehicle_id, timestamp, transformed, active_drive)
    db.add(position)
    await db.flush()
    
    # Update drive start_position_id if this is the first position in a new drive
    if active_drive and drive_started:
        active_drive.start_position_id = position.id
    
    return position, active_drive, active_charging_session


async def _handle_drive_detection(
    db: AsyncSession,
    vehicle_id: int,
    timestamp: datetime,
    transformed: dict,
    current_gear: Optional[str],
    existing_active_drive: Optional[Drive],
) -> Tuple[Optional[Drive], bool]:
    """Handle drive start/end detection and updates.
    
    Returns:
        Tuple of (active_drive, drive_started)
    """
    drive_started = False
    
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
        await db.flush()
        return active_drive, drive_started
    
    elif current_gear == "P" and existing_active_drive:
        # Drive end: gear changed to Park
        logger.info(f"Drive ended for vehicle {vehicle_id}")
        ended_drive = existing_active_drive
        
        ended_drive.end_date = timestamp
        ended_drive.end_km = transformed.get("odometer")
        ended_drive.end_battery_range_km = transformed.get("battery_range_km")
        
        # Calculate aggregates from positions in this drive
        await _calculate_drive_aggregates(db, ended_drive)
        
        return None, False  # Drive has ended
    
    else:
        # Continue existing drive or no drive
        return existing_active_drive, False


async def _calculate_drive_aggregates(db: AsyncSession, drive: Drive) -> None:
    """Calculate aggregate statistics for a completed drive."""
    from database.models import Position
    
    positions_result = await db.execute(
        select(Position)
        .where(Position.drive_id == drive.id)
        .order_by(Position.timestamp.asc())
    )
    drive_positions = positions_result.scalars().all()
    
    if not drive_positions:
        return
    
    speeds = [p.speed for p in drive_positions if p.speed is not None]
    powers = [p.power for p in drive_positions if p.power is not None]
    temps = [p.outside_temp for p in drive_positions if p.outside_temp is not None]
    
    if speeds:
        drive.speed_max = max(speeds)
    if powers:
        drive.power_max = max(powers)
        drive.power_min = min(powers)
        drive.power_avg = int(sum(powers) / len(powers))
    if temps:
        drive.outside_temp_avg = sum(temps) / len(temps)
    
    if drive.start_km and drive.end_km:
        drive.distance = float(drive.end_km) - float(drive.start_km)
    
    if drive.start_date and drive.end_date:
        duration_seconds = (drive.end_date - drive.start_date).total_seconds()
        drive.duration_min = int(duration_seconds / 60)
    
    # Set start and end position IDs
    drive.start_position_id = drive_positions[0].id
    drive.end_position_id = drive_positions[-1].id


async def _handle_charging_session(
    db: AsyncSession,
    vehicle_id: int,
    timestamp: datetime,
    transformed: dict,
    current_charging: Optional[bool],
) -> Optional[ChargingSession]:
    """Handle charging session start/end detection and updates.
    
    Returns:
        Active charging session if any, None otherwise
    """
    # Check for existing active charging session
    prev_session_result = await db.execute(
        select(ChargingSession)
        .where(ChargingSession.vehicle_id == vehicle_id)
        .where(ChargingSession.end_date.is_(None))
        .order_by(ChargingSession.start_date.desc())
        .limit(1)
    )
    existing_active_session = prev_session_result.scalar_one_or_none()
    prev_charging = existing_active_session is not None
    
    if not prev_charging and current_charging is True:
        # Charging start
        logger.info(f"Charging started for vehicle {vehicle_id}")
        active_session = ChargingSession(
            vehicle_id=vehicle_id,
            start_date=timestamp,
            start_battery_level=transformed.get("battery_level"),
        )
        db.add(active_session)
        await db.flush()
        return active_session
    
    elif prev_charging is True and current_charging is False:
        # Charging end
        logger.info(f"Charging ended for vehicle {vehicle_id}")
        if existing_active_session:
            existing_active_session.end_date = timestamp
            existing_active_session.end_battery_level = transformed.get("battery_level")
            
            # Calculate duration
            if existing_active_session.start_date:
                duration_seconds = (timestamp - existing_active_session.start_date).total_seconds()
                existing_active_session.duration_min = int(duration_seconds / 60)
        
        return None  # Charging has ended
    
    else:
        # Continue existing charging session or no charging
        return existing_active_session


def _create_position(
    vehicle_id: int,
    timestamp: datetime,
    transformed: dict,
    active_drive: Optional[Drive],
) -> Position:
    """Create a Position record from transformed data.
    
    Args:
        vehicle_id: Vehicle ID
        timestamp: Position timestamp
        transformed: Transformed telemetry data
        active_drive: Active drive if any
    
    Returns:
        Position model instance
    """
    from database.models import Position
    
    # Handle GPS coordinates (can be None for parked vehicles)
    lat = transformed.get("latitude") or 0.0
    lon = transformed.get("longitude") or 0.0
    
    return Position(
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

