"""SQLAlchemy models for the database."""
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from database.connection import Base


class Vehicle(Base):
    """Vehicle model."""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(50), unique=True, index=True, nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships - disabled lazy loading to avoid schema mismatch issues
    positions = relationship("Position", back_populates="vehicle", cascade="all, delete-orphan", foreign_keys="[Position.vehicle_id]", lazy="noload")
    drives = relationship("Drive", back_populates="vehicle", cascade="all, delete-orphan", foreign_keys="[Drive.vehicle_id]", lazy="noload")
    charging_sessions = relationship("ChargingSession", back_populates="vehicle", cascade="all, delete-orphan", lazy="noload")


class Position(Base):
    """Telemetry position snapshot model."""
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}  # Allow model to work with existing table

    id = Column(Integer, primary_key=True, index=True)
    
    # Vehicle reference and timestamp
    vehicle_id = Column(SmallInteger, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # GPS fields (can be None for parked vehicles without GPS)
    latitude = Column(Numeric(8, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    heading = Column(Numeric(5, 2), nullable=True)
    gps_accuracy = Column(Numeric(8, 2), nullable=True)
    
    # Vehicle metrics
    speed = Column(SmallInteger, nullable=True)  # km/h
    odometer = Column(Numeric(10, 2), nullable=True)  # km
    battery_level = Column(SmallInteger, nullable=True)  # 0-100
    battery_range_km = Column(Numeric(6, 2), nullable=True)
    outside_temp = Column(Numeric(4, 1), nullable=True)  # Celsius
    inside_temp = Column(Numeric(4, 1), nullable=True)  # Celsius
    power = Column(SmallInteger, nullable=True)  # kW
    
    # AC fields
    is_climate_on = Column(Boolean, nullable=True)
    driver_temp_setting = Column(Numeric(4, 1), nullable=True)  # Celsius
    passenger_temp_setting = Column(Numeric(4, 1), nullable=True)  # Celsius
    is_rear_defroster_on = Column(Boolean, nullable=True)
    is_front_defroster_on = Column(Boolean, nullable=True)
    
    # Gear and AC fields
    gear_position = Column(String(10), nullable=True)
    fan_level = Column(SmallInteger, nullable=True)
    wind_mode = Column(String(20), nullable=True)
    cycle_mode = Column(String(10), nullable=True)
    
    # Tire pressures
    tire_pressure_fl = Column(Numeric(4, 1), nullable=True)
    tire_pressure_fr = Column(Numeric(4, 1), nullable=True)
    tire_pressure_rl = Column(Numeric(4, 1), nullable=True)
    tire_pressure_rr = Column(Numeric(4, 1), nullable=True)
    
    # Tire temperatures
    tire_temp_fl = Column(Numeric(4, 1), nullable=True)
    tire_temp_fr = Column(Numeric(4, 1), nullable=True)
    tire_temp_rl = Column(Numeric(4, 1), nullable=True)
    tire_temp_rr = Column(Numeric(4, 1), nullable=True)
    
    # Air quality
    pm25_inside = Column(SmallInteger, nullable=True)
    pm25_outside = Column(SmallInteger, nullable=True)
    
    # Drive relationship
    drive_id = Column(Integer, ForeignKey("drives.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="positions", foreign_keys=[vehicle_id])
    drive = relationship("Drive", back_populates="positions", foreign_keys=[drive_id])


class Drive(Base):
    """Drive/trip model."""
    __tablename__ = "drives"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(SmallInteger, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Position references
    start_position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    end_position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    
    # Aggregated metrics
    distance = Column(Numeric(8, 2), nullable=True)  # km
    duration_min = Column(SmallInteger, nullable=True)  # minutes
    speed_max = Column(SmallInteger, nullable=True)  # km/h
    power_max = Column(SmallInteger, nullable=True)  # kW
    power_min = Column(SmallInteger, nullable=True)  # kW
    power_avg = Column(SmallInteger, nullable=True)  # kW
    
    # Odometer readings
    start_km = Column(Numeric(10, 2), nullable=True)
    end_km = Column(Numeric(10, 2), nullable=True)
    
    # Battery ranges
    start_battery_range_km = Column(Numeric(6, 2), nullable=True)
    end_battery_range_km = Column(Numeric(6, 2), nullable=True)
    
    # Temperature averages
    outside_temp_avg = Column(Numeric(4, 1), nullable=True)
    inside_temp_avg = Column(Numeric(4, 1), nullable=True)
    
    # Elevation changes
    ascent = Column(Integer, nullable=True)  # meters
    descent = Column(Integer, nullable=True)  # meters
    
    # Addresses (optional, for reverse geocoding)
    start_address = Column(Text, nullable=True)
    end_address = Column(Text, nullable=True)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="drives", foreign_keys=[vehicle_id])
    positions = relationship("Position", back_populates="drive", foreign_keys=[Position.drive_id])
    start_position = relationship("Position", foreign_keys=[start_position_id], post_update=True)
    end_position = relationship("Position", foreign_keys=[end_position_id], post_update=True)


class ChargingSession(Base):
    """Charging session model."""
    __tablename__ = "charging_sessions"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(SmallInteger, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Battery levels
    start_battery_level = Column(SmallInteger, nullable=True)
    end_battery_level = Column(SmallInteger, nullable=True)
    
    # Energy
    charge_energy_added = Column(Numeric(8, 2), nullable=True)  # kWh
    duration_min = Column(SmallInteger, nullable=True)  # minutes
    
    # Temperature
    outside_temp_avg = Column(Numeric(4, 1), nullable=True)
    
    # Position reference (where charging started)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="charging_sessions")
    position = relationship("Position", foreign_keys=[position_id])
    charging_data_points = relationship("ChargingDataPoint", back_populates="charging_session", cascade="all, delete-orphan")


class ChargingDataPoint(Base):
    """Individual charging measurement model."""
    __tablename__ = "charging_data_points"

    id = Column(Integer, primary_key=True, index=True)
    charging_session_id = Column(Integer, ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Battery
    battery_level = Column(SmallInteger, nullable=True)
    charge_energy_added = Column(Numeric(8, 2), nullable=True)  # kWh (cumulative)
    
    # Charger info
    charger_power = Column(SmallInteger, nullable=True)  # kW
    charger_voltage = Column(SmallInteger, nullable=True)  # V
    charger_current = Column(SmallInteger, nullable=True)  # A
    
    # Temperature
    outside_temp = Column(Numeric(4, 1), nullable=True)
    
    # Relationships
    charging_session = relationship("ChargingSession", back_populates="charging_data_points")


# Create indexes for spatial queries (requires cube/earthdistance extensions)
# These are optional but recommended for geofence/distance features
try:
    Index(
        'idx_positions_location',
        func('ll_to_earth', Position.latitude, Position.longitude),
        postgresql_using='gist'
    )
except Exception:
    # Index creation will fail if extensions aren't installed, that's okay
    pass

