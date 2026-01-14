"""BYDAutoChargingDevice transformer."""
from typing import Dict, Any, Optional
from telemetry.devices.common import to_boolean, convert_power_to_kw


def transform_charging(device_data: Dict, power_unit: Optional[int]) -> Dict[str, Any]:
    """Transform charging device data.
    
    Args:
        device_data: BYDAutoChargingDevice data
        power_unit: Power unit from instrument device (1 = kW, 2 = HP)
    
    Returns:
        Dictionary with transformed charging fields
    """
    return {
        "is_charging": to_boolean(device_data.get("getChargingState")),
        "charging_gun_connected": to_boolean(
            device_data.get("getChargingGunState"),
            true_values={2}  # 2 = connected, 1 = not connected
        ),
        "charger_power": convert_power_to_kw(
            device_data.get("getChargingPower"),
            power_unit
        ),
        "charge_energy_added": None,  # Cumulative, will be calculated
    }

