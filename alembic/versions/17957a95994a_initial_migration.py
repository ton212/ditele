"""Initial migration

Revision ID: 17957a95994a
Revises: 
Create Date: 2026-01-15 02:59:13.987982

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17957a95994a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Install PostgreSQL extensions for geospatial features
    op.execute("CREATE EXTENSION IF NOT EXISTS cube")
    op.execute("CREATE EXTENSION IF NOT EXISTS earthdistance")
    
    # Check if tables already exist (in case TeslaMate tables are present)
    # We'll create our tables only if they don't exist
    conn = op.get_bind()
    
    # Check if vehicles table exists
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'vehicles'
        )
    """))
    vehicles_exists = result.scalar()
    
    if not vehicles_exists:
        # Create vehicles first (no dependencies)
        op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vin', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vehicles_id'), 'vehicles', ['id'], unique=False)
        op.create_index(op.f('ix_vehicles_vin'), 'vehicles', ['vin'], unique=True)
    
    # Check if our positions table exists (different from TeslaMate's)
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'positions'
            AND column_name = 'heading'
        )
    """))
    our_positions_exists = result.scalar()
    
    if not our_positions_exists:
        # Add our new columns to existing positions table if it exists, or create new one
        result = conn.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'positions'
            )
        """))
        positions_table_exists = result.scalar()
        
        if positions_table_exists:
            # Add our new columns to existing positions table
            try:
                op.add_column('positions', sa.Column('heading', sa.Numeric(precision=5, scale=2), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('gps_accuracy', sa.Numeric(precision=8, scale=2), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('gear_position', sa.String(length=10), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('fan_level', sa.SmallInteger(), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('wind_mode', sa.String(length=20), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('cycle_mode', sa.String(length=10), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_pressure_fl', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_pressure_fr', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_pressure_rl', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_pressure_rr', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_temp_fl', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_temp_fr', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_temp_rl', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('tire_temp_rr', sa.Numeric(precision=4, scale=1), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('pm25_inside', sa.SmallInteger(), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('pm25_outside', sa.SmallInteger(), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('positions', sa.Column('battery_range_km', sa.Numeric(precision=6, scale=2), nullable=True))
            except Exception:
                pass
            # Make latitude/longitude nullable if they're not already
            try:
                op.alter_column('positions', 'latitude', nullable=True)
            except Exception:
                pass
            try:
                op.alter_column('positions', 'longitude', nullable=True)
            except Exception:
                pass
            # Rename car_id to vehicle_id if needed
            try:
                op.alter_column('positions', 'car_id', new_column_name='vehicle_id')
            except Exception:
                pass
            # Rename date to timestamp if needed
            try:
                op.alter_column('positions', 'date', new_column_name='timestamp')
            except Exception:
                pass
        else:
            # Create positions table from scratch
            op.create_table('positions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('vehicle_id', sa.SmallInteger(), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('latitude', sa.Numeric(precision=8, scale=6), nullable=True),
            sa.Column('longitude', sa.Numeric(precision=9, scale=6), nullable=True),
            sa.Column('heading', sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column('gps_accuracy', sa.Numeric(precision=8, scale=2), nullable=True),
            sa.Column('speed', sa.SmallInteger(), nullable=True),
            sa.Column('odometer', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('battery_level', sa.SmallInteger(), nullable=True),
            sa.Column('battery_range_km', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('outside_temp', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('inside_temp', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('gear_position', sa.String(length=10), nullable=True),
            sa.Column('power', sa.SmallInteger(), nullable=True),
            sa.Column('is_climate_on', sa.Boolean(), nullable=True),
            sa.Column('driver_temp_setting', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('passenger_temp_setting', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('fan_level', sa.SmallInteger(), nullable=True),
            sa.Column('wind_mode', sa.String(length=20), nullable=True),
            sa.Column('cycle_mode', sa.String(length=10), nullable=True),
            sa.Column('is_rear_defroster_on', sa.Boolean(), nullable=True),
            sa.Column('is_front_defroster_on', sa.Boolean(), nullable=True),
            sa.Column('tire_pressure_fl', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_pressure_fr', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_pressure_rl', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_pressure_rr', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_temp_fl', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_temp_fr', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_temp_rl', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('tire_temp_rr', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('pm25_inside', sa.SmallInteger(), nullable=True),
            sa.Column('pm25_outside', sa.SmallInteger(), nullable=True),
            sa.Column('drive_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
            )
            op.create_index(op.f('ix_positions_drive_id'), 'positions', ['drive_id'], unique=False)
            op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
            op.create_index(op.f('ix_positions_timestamp'), 'positions', ['timestamp'], unique=False)
            op.create_index(op.f('ix_positions_vehicle_id'), 'positions', ['vehicle_id'], unique=False)
    
    # Create spatial index on positions (requires cube/earthdistance extensions)
    try:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_location 
            ON positions USING gist (ll_to_earth(latitude, longitude))
        """)
    except Exception:
        pass
    
    # Check if our drives table needs updates
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'drives'
            AND column_name = 'power_avg'
        )
    """))
    our_drives_exists = result.scalar()
    
    if not our_drives_exists:
        result = conn.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'drives'
            )
        """))
        drives_table_exists = result.scalar()
        
        if drives_table_exists:
            # Add missing columns
            try:
                op.add_column('drives', sa.Column('power_avg', sa.SmallInteger(), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('drives', sa.Column('start_battery_range_km', sa.Numeric(precision=6, scale=2), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('drives', sa.Column('end_battery_range_km', sa.Numeric(precision=6, scale=2), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('drives', sa.Column('start_address', sa.Text(), nullable=True))
            except Exception:
                pass
            try:
                op.add_column('drives', sa.Column('end_address', sa.Text(), nullable=True))
            except Exception:
                pass
            # Rename car_id to vehicle_id if needed
            try:
                op.alter_column('drives', 'car_id', new_column_name='vehicle_id')
            except Exception:
                pass
        else:
            # Create drives table
            op.create_table('drives',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('vehicle_id', sa.SmallInteger(), nullable=False),
            sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('start_position_id', sa.Integer(), nullable=True),
            sa.Column('end_position_id', sa.Integer(), nullable=True),
            sa.Column('distance', sa.Numeric(precision=8, scale=2), nullable=True),
            sa.Column('duration_min', sa.SmallInteger(), nullable=True),
            sa.Column('speed_max', sa.SmallInteger(), nullable=True),
            sa.Column('power_max', sa.SmallInteger(), nullable=True),
            sa.Column('power_min', sa.SmallInteger(), nullable=True),
            sa.Column('power_avg', sa.SmallInteger(), nullable=True),
            sa.Column('start_km', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('end_km', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('start_battery_range_km', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('end_battery_range_km', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('outside_temp_avg', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('inside_temp_avg', sa.Numeric(precision=4, scale=1), nullable=True),
            sa.Column('ascent', sa.Integer(), nullable=True),
            sa.Column('descent', sa.Integer(), nullable=True),
            sa.Column('start_address', sa.Text(), nullable=True),
            sa.Column('end_address', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['end_position_id'], ['positions.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['start_position_id'], ['positions.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
            )
            op.create_index(op.f('ix_drives_id'), 'drives', ['id'], unique=False)
            op.create_index(op.f('ix_drives_start_date'), 'drives', ['start_date'], unique=False)
            op.create_index(op.f('ix_drives_vehicle_id'), 'drives', ['vehicle_id'], unique=False)
    
    # Add drive_id foreign key to positions if it doesn't exist
    try:
        op.create_foreign_key('positions_drive_id_fkey', 'positions', 'drives', ['drive_id'], ['id'], ondelete='SET NULL')
    except Exception:
        pass
    
    # Create charging_sessions table
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'charging_sessions'
        )
    """))
    if not result.scalar():
        op.create_table('charging_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.SmallInteger(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_battery_level', sa.SmallInteger(), nullable=True),
        sa.Column('end_battery_level', sa.SmallInteger(), nullable=True),
        sa.Column('charge_energy_added', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('duration_min', sa.SmallInteger(), nullable=True),
        sa.Column('outside_temp_avg', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_charging_sessions_id'), 'charging_sessions', ['id'], unique=False)
        op.create_index(op.f('ix_charging_sessions_start_date'), 'charging_sessions', ['start_date'], unique=False)
        op.create_index(op.f('ix_charging_sessions_vehicle_id'), 'charging_sessions', ['vehicle_id'], unique=False)
    
    # Create charging_data_points table
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'charging_data_points'
        )
    """))
    if not result.scalar():
        op.create_table('charging_data_points',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('charging_session_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('battery_level', sa.SmallInteger(), nullable=True),
        sa.Column('charge_energy_added', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('charger_power', sa.SmallInteger(), nullable=True),
        sa.Column('charger_voltage', sa.SmallInteger(), nullable=True),
        sa.Column('charger_current', sa.SmallInteger(), nullable=True),
        sa.Column('outside_temp', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.ForeignKeyConstraint(['charging_session_id'], ['charging_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_charging_data_points_charging_session_id'), 'charging_data_points', ['charging_session_id'], unique=False)
        op.create_index(op.f('ix_charging_data_points_id'), 'charging_data_points', ['id'], unique=False)
        op.create_index(op.f('ix_charging_data_points_timestamp'), 'charging_data_points', ['timestamp'], unique=False)


def downgrade():
    # Drop our custom tables (but keep TeslaMate tables if they exist)
    op.drop_index(op.f('ix_charging_data_points_timestamp'), table_name='charging_data_points')
    op.drop_index(op.f('ix_charging_data_points_id'), table_name='charging_data_points')
    op.drop_index(op.f('ix_charging_data_points_charging_session_id'), table_name='charging_data_points')
    op.drop_table('charging_data_points')
    op.drop_index(op.f('ix_charging_sessions_vehicle_id'), table_name='charging_sessions')
    op.drop_index(op.f('ix_charging_sessions_start_date'), table_name='charging_sessions')
    op.drop_index(op.f('ix_charging_sessions_id'), table_name='charging_sessions')
    op.drop_table('charging_sessions')
    op.drop_index(op.f('ix_vehicles_vin'), table_name='vehicles')
    op.drop_index(op.f('ix_vehicles_id'), table_name='vehicles')
    op.drop_table('vehicles')
    # Note: We don't drop positions/drives as they may be TeslaMate tables
