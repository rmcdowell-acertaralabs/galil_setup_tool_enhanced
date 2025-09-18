# galil_compat.py
# Galil command compatibility helpers for correct syntax

def cmd_tp(axis: str) -> str: 
    """Position query - returns TPA, TPB, etc."""
    return f"TP{axis}"

def cmd_sh(axis: str) -> str: 
    """Servo enable - returns SHA, SHB, etc."""
    return f"SH{axis}"

def cmd_mo(axis: str) -> str: 
    """Motor off - returns MOA, MOB, etc."""
    return f"MO{axis}"

def cmd_bg(axis: str) -> str: 
    """Begin motion - returns BGA, BGB, etc."""
    return f"BG{axis}"

def cmd_am(axis: str) -> str: 
    """After motion - returns AMA, AMB, etc."""
    return f"AM{axis}"

def cmd_sp(axis: str, v: int) -> str: 
    """Speed set - returns SPA=5000, SPB=5000, etc."""
    return f"SP{axis}={int(v)}"

def cmd_ac(axis: str, v: int) -> str: 
    """Acceleration set - returns ACA=2500, ACB=2500, etc."""
    return f"AC{axis}={int(v)}"

def cmd_dc(axis: str, v: int) -> str: 
    """Deceleration set - returns DCA=2500, DCB=2500, etc."""
    return f"DC{axis}={int(v)}"

def cmd_pa(axis: str, v: int) -> str: 
    """Position absolute - returns PAA=152897, PAB=152264, etc."""
    return f"PA{axis}={int(v)}"

def cmd_sc(axis: str) -> str: 
    """Stop code - returns SCA, SCB, etc."""
    return f"SC{axis}"

def id_cmd() -> str: 
    """Identity command - returns ID"""
    return "ID"

def tb_cmd() -> str: 
    """Status byte - returns TB"""
    return "TB"

def bv_cmd() -> str: 
    """Axes count - returns MG _BV"""
    return "MG _BV"

def bn_cmd() -> str: 
    """Serial number - returns MG _BN"""
    return "MG _BN"

def ta_bank(bank: int) -> str: 
    """Amplifier error bank - returns MG _TA0, MG _TA1, etc."""
    return f"MG _TA{bank}"

def ts_axis(axis: str) -> str: 
    """Axis status - returns MG _TSA, MG _TSB, etc."""
    return f"MG _TS{axis}"

def tc_cmd() -> str:
    """Tell error code - returns TC"""
    return "TC"

def tc_message_cmd() -> str:
    """Tell error code with message - returns TC 1"""
    return "TC 1"

def sanity_probe(g):
    """Minimal sanity probe to test basic controller communication"""
    print("=== Galil Controller Sanity Probe ===")
    
    # Test identity
    try:
        id_response = g.GCommand(id_cmd())
        print(f"ID: {id_response.strip()}")
    except Exception as e:
        print(f"ID command failed: {e}")
    
    # Test status byte
    try:
        tb_response = g.GCommand(tb_cmd())
        print(f"TB: {tb_response.strip()}")
    except Exception as e:
        print(f"TB command failed: {e}")
    
    # Test axes count
    try:
        bv_response = g.GCommand(bv_cmd())
        print(f"Axes count (_BV): {bv_response.strip()}")
    except Exception as e:
        print(f"_BV command failed: {e}")
    
    # Test one axis (A)
    try:
        sh_response = g.GCommand(cmd_sh("A"))
        print(f"SHA: {sh_response.strip() or 'OK'}")
    except Exception as e:
        print(f"SHA command failed: {e}")
    
    try:
        tp_response = g.GCommand(cmd_tp("A"))
        print(f"TPA: {tp_response.strip()}")
    except Exception as e:
        print(f"TPA command failed: {e}")
    
    print("=== End Sanity Probe ===")
