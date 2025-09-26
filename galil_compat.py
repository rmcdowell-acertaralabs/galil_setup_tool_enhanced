# galil_compat.py
# Galil command compatibility helpers for correct syntax
# Updated to match command_validator.py definitions

# === AXIS COMMANDS ===

def cmd_tp(axis: str) -> str: 
    """Tell Position - returns TPA, TPB, etc."""
    return f"TP{axis}"

def cmd_sh(axis: str) -> str: 
    """Servo Here (Enable) - returns SHA, SHB, etc."""
    return f"SH{axis}"

def cmd_mo(axis: str) -> str: 
    """Motor Off - returns MOA, MOB, etc."""
    return f"MO{axis}"

def cmd_bg(axis: str) -> str: 
    """Begin Motion - returns BGA, BGB, etc."""
    return f"BG{axis}"

def cmd_am(axis: str) -> str: 
    """After Motion - returns AMA, AMB, etc."""
    return f"AM{axis}"

def cmd_sp(axis: str, v: int) -> str: 
    """Speed - returns SPA=5000, SPB=5000, etc."""
    return f"SP{axis}={int(v)}"

def cmd_ac(axis: str, v: int) -> str: 
    """Acceleration - returns ACA=2500, ACB=2500, etc."""
    return f"AC{axis}={int(v)}"

def cmd_dc(axis: str, v: int) -> str: 
    """Deceleration - returns DCA=2500, DCB=2500, etc."""
    return f"DC{axis}={int(v)}"

def cmd_pa(axis: str, v: int) -> str: 
    """Position Absolute - returns PAA=152897, PAB=152264, etc."""
    return f"PA{axis}={int(v)}"

def cmd_dp(axis: str, v: int) -> str: 
    """Define Position - returns DPA=0, DPB=0, etc."""
    return f"DP{axis}={int(v)}"

def cmd_pr(axis: str, v: int) -> str: 
    """Position Relative - returns PRA=1000, PRB=-500, etc."""
    return f"PR{axis}={int(v)}"

def cmd_jg(axis: str, v: int) -> str: 
    """Jog - returns JGA=1000, JGB=-500, etc."""
    return f"JG{axis}={int(v)}"

def cmd_fi(axis: str) -> str: 
    """Find Index - returns FIA, FIB, etc."""
    return f"FI{axis}"

# === BRUSHLESS MOTOR COMMANDS ===

def cmd_ba(axis: str) -> str: 
    """Brushless Amplifier - returns BAA, BAB, etc."""
    return f"BA{axis}"

def cmd_bm(axis: str, v: int) -> str: 
    """Brushless Modulo - returns BMA=16000, BMB=16000, etc."""
    return f"BM{axis}={int(v)}"

def cmd_bx(axis: str, v: str) -> str: 
    """Brushless eXchange - returns BXA=<value>, BXB=<value>, etc."""
    return f"BX{axis}={v}"

def cmd_bz(axis: str, v: str) -> str: 
    """Brushless Zero - returns BZA=<value>, BZB=<value>, etc."""
    return f"BZ{axis}={v}"

def cmd_bc(axis: str) -> str: 
    """Brushless Calibrate - returns BCA, BCB, etc."""
    return f"BC{axis}"

def cmd_bi(axis: str, v: int) -> str: 
    """Brushless Input - returns BIA=0, BIB=1, etc."""
    return f"BI{axis}={int(v)}"

# === ENCODER AND LATCH COMMANDS ===

def cmd_ce(axis: str, v: int) -> str: 
    """Count Enable - returns CEA=1, CEB=0, etc."""
    return f"CE{axis}={int(v)}"

def cmd_al(axis: str) -> str: 
    """After Latch - returns ALA, ALB, etc."""
    return f"AL{axis}"

def cmd_rl(axis: str) -> str: 
    """Read Latch - returns RLA, RLB, etc."""
    return f"RL{axis}"

# === ERROR AND LIMIT COMMANDS ===

def cmd_oe(axis: str, v: int) -> str: 
    """Off on Error - returns OEA=1, OEB=0, etc."""
    return f"OE{axis}={int(v)}"

def cmd_er(axis: str, v: int) -> str: 
    """Error Limit - returns ERA=1000, ERB=1000, etc."""
    return f"ER{axis}={int(v)}"

def cmd_fl(axis: str, v: int) -> str: 
    """Forward Software Limit - returns FLA=100000, FLB=100000, etc."""
    return f"FL{axis}={int(v)}"

def cmd_bl(axis: str, v: int) -> str: 
    """Backward Software Limit - returns BLA=-100000, BLB=-100000, etc."""
    return f"BL{axis}={int(v)}"

def cmd_sl(axis: str, v: int) -> str: 
    """Software Limit - returns SLA=100000, SLB=100000, etc."""
    return f"SL{axis}={int(v)}"

# === TORQUE AND GAIN COMMANDS ===

def cmd_tl(axis: str, v: int) -> str: 
    """Torque Limit - returns TLA=1000, TLB=1000, etc."""
    return f"TL{axis}={int(v)}"

def cmd_tk(axis: str, v: int) -> str: 
    """Torque Bias - returns TKA=0, TKB=0, etc."""
    return f"TK{axis}={int(v)}"

def cmd_of(axis: str, v: int) -> str: 
    """DAC Offset - returns OFA=0, OFB=0, etc."""
    return f"OF{axis}={int(v)}"

def cmd_kp(axis: str, v: float) -> str: 
    """Proportional Gain - returns KPA=1.0, KPB=1.0, etc."""
    return f"KP{axis}={v}"

def cmd_ki(axis: str, v: float) -> str: 
    """Integral Gain - returns KIA=0.1, KIB=0.1, etc."""
    return f"KI{axis}={v}"

def cmd_kd(axis: str, v: float) -> str: 
    """Derivative Gain - returns KDA=0.01, KDB=0.01, etc."""
    return f"KD{axis}={v}"

# === GENERAL COMMANDS ===

def cmd_st() -> str: 
    """Stop Motion - returns ST"""
    return "ST"

def cmd_te() -> str: 
    """Tell Error Code - returns TE"""
    return "TE"

def cmd_tc() -> str:
    """Tell Error Text - returns TC"""
    return "TC"

def cmd_tc_message() -> str:
    """Tell Error Text with message - returns TC 1"""
    return "TC 1"

def cmd_mg(variable: str) -> str: 
    """Message - returns MG <variable>"""
    return f"MG {variable}"

def cmd_wt(time: float) -> str: 
    """Wait - returns WT 1000"""
    return f"WT {time}"

def cmd_mt(motor_list: str) -> str: 
    """Motor Type - returns MT A,B"""
    return f"MT {motor_list}"

# === OPERAND QUERIES ===

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

# === LEGACY COMMANDS (not in validator but kept for compatibility) ===

def cmd_sc(axis: str) -> str: 
    """Stop Code - returns SCA, SCB, etc. (legacy command)"""
    return f"SC{axis}"

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
