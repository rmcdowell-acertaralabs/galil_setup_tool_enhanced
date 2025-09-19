# diag_axis.py
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class AxisInfo:
    axis: str
    mode: str          # 'servo', 'stepper', or 'unknown'
    mt_raw: Optional[float]
    enabled: bool
    note: str = ""

def _parse_tc_number(tc_text: str) -> Optional[int]:
    """Parse TC error code number from TC response"""
    # tc_text examples: "0" or "119 Not valid for axis configured as stepper"
    try:
        return int(str(tc_text).strip().split()[0])
    except Exception:
        return None

def read_motor_type(io, axis: str) -> Optional[float]:
    """Read motor type for axis - try operand first, then MT ? fallback"""
    # Try operand first (preferred)
    try:
        return io.num(f"MG _MT{axis}")
    except Exception:
        pass
    # Fallback: MT ? returns a list; pick last numeric token via io.num()
    try:
        return io.num("MT ?")
    except Exception:
        return None

def classify_mode(mt: Optional[float]) -> str:
    """Classify motor type as servo, stepper, or unknown"""
    # Galil MT conventions (simplified):
    # 1, -1, 1.5, -1.5, 3-style => servo/brushless families
    # 2, -2, 2.5, -2.5          => stepper families
    if mt is None:
        return "unknown"
    if int(abs(round(mt))) == 2:
        return "stepper"
    return "servo"

def safe_enable_if_needed(io, axis: str, mode: str) -> Tuple[bool, str]:
    """
    Safe servo enable that handles steppers properly:
    - Servo: MO -> AZ1 -> SH, verify _MOx==0
    - Stepper: skip SH (not valid), just return enabled=True logically
    - Unknown: attempt SH once; decode TC if it fails
    """
    if mode == "stepper":
        # SH not required/valid; motion commands will still work.
        return True, "Stepper: skipping SH."
    
    try:
        # Clear any latched amp faults before SH
        io.mo(axis)
        io.clear_amp_latched()
        io.sh(axis)  # may raise -> we'll annotate with TC
        mo = io.i32(f"MG _MO{axis}")
        if mo != 0:
            return False, f"_MO{axis}={mo} after SH (motor off)."
        return True, "Servo enabled."
    except Exception:
        tc = io.tc_text()
        code = _parse_tc_number(tc)
        if code == 119:
            return True, "Axis is stepper (TC=119); skipping SH."
        if code in (111, 110):
            return False, f"Brushless not initialized (TC={tc}). Run BA/BZ per axis first."
        return False, f"SH failed (TC={tc})."
