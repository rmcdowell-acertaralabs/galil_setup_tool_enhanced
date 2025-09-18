# galil_io.py
import threading, re
from typing import Tuple

class GalilIO:
    """
    Thin, threadsafe adapter around a real gclib handle (must have .GCommand()).
    - serializes access (prevents interleaving with background pollers)
    - disables echo for clean responses
    - provides numeric-safe helpers (float -> int), per-axis commands
    """
    def __init__(self, gclib_handle):
        if not hasattr(gclib_handle, "GCommand"):
            raise TypeError("GalilIO requires a gclib handle with .GCommand()")
        self.g = gclib_handle
        self._lock = threading.RLock()
        # best-effort: silence echo so responses are clean
        try: 
            self.cmd("EO 0")
        except: 
            pass

    # ---- low-level ----
    def cmd(self, s: str) -> str:
        with self._lock:
            r = self.g.GCommand(s)
        return (r or "").strip()

    def num(self, s: str) -> float:
        # pick the LAST numeric token in the reply; tolerates interleaved noise
        reply = self.cmd(s)
        nums = re.findall(r'[-+]?\d+(?:\.\d+)?', reply)
        if not nums:
            raise ValueError(f"Expected numeric reply to {s!r}, got {reply!r}")
        return float(nums[-1])

    def i32(self, s: str) -> int:
        return int(round(self.num(s)))

    # ---- per-axis helpers (suffix syntax, no spaces) ----
    @staticmethod
    def norm_axis(axis: str) -> str:
        axis = axis.upper()
        if axis not in "ABCDEFGH":
            raise ValueError(f"Bad axis: {axis}")
        return axis

    def id(self) -> str: 
        return self.cmd("ID")
    
    def tb(self) -> int:  
        return self.i32("TB")
    
    def bv(self) -> int:  
        return self.i32("MG _BV")
    
    def bn(self) -> int:  
        return self.i32("MG _BN")

    def sh(self, axis: str) -> None: 
        self.cmd(f"SH{self.norm_axis(axis)}")
    
    def mo(self, axis: str) -> None: 
        self.cmd(f"MO{self.norm_axis(axis)}")
    
    def sp(self, axis: str, v: int) -> None: 
        self.cmd(f"SP{self.norm_axis(axis)}={int(v)}")
    
    def ac(self, axis: str, v: int) -> None: 
        self.cmd(f"AC{self.norm_axis(axis)}={int(v)}")
    
    def dc(self, axis: str, v: int) -> None: 
        self.cmd(f"DC{self.norm_axis(axis)}={int(v)}")
    
    def pa(self, axis: str, v: int) -> None: 
        self.cmd(f"PA{self.norm_axis(axis)}={int(v)}")
    
    def pr(self, axis: str, v: int) -> None: 
        self.cmd(f"PR{self.norm_axis(axis)}={int(v)}")
    
    def bg(self, axis: str) -> None:        
        self.cmd(f"BG{self.norm_axis(axis)}")
    
    def am(self, axis: str) -> None:        
        self.cmd(f"AM{self.norm_axis(axis)}")
    
    def tp(self, axis: str) -> int:         
        return self.i32(f"TP{self.norm_axis(axis)}")
    
    def sc(self, axis: str) -> int:         
        return self.i32(f"SC{self.norm_axis(axis)}")
    
    def ts(self, axis: str) -> int:         
        return self.i32(f"MG _TS{self.norm_axis(axis)}")

    # amplifier status (banks only on 41x3)
    def ta_or(self) -> int:
        return (self.i32("MG _TA0") |
                self.i32("MG _TA1") |
                self.i32("MG _TA2") |
                self.i32("MG _TA3"))

    # error code (with human text if present)
    def tc_text(self) -> str:
        if self.i32("MG _TC") == 0:
            return "0"
        return self.cmd("TC 1")  # e.g. "1 Unrecognized command"

    # latched amp clear (per manual: best when MO)
    def clear_amp_latched(self) -> None:
        self.cmd("AZ1")
        self.cmd("WT 2")

def safe_enable(io: GalilIO, axis: str) -> None:
    """Safely enable servo with proper error handling"""
    axis = axis.upper()
    # Clear any latched amp faults before enabling
    io.mo(axis)
    io.clear_amp_latched()
    # Try to enable
    try:
        io.sh(axis)
    except Exception:
        # Show why
        raise RuntimeError(f"SH{axis} failed; TC={io.tc_text()}")
    # Verify: _MOx == 0 means servo here (motor ON)
    mo = io.i32(f"MG _MO{axis}")
    if mo != 0:
        # If OE is forcing it off due to immediate error, show TS/TA/TE/SC
        ts = io.ts(axis)
        sc = io.sc(axis)
        te = io.i32(f"TE{axis}")
        ta = io.ta_or()
        raise RuntimeError(
            f"Axis {axis} not servoed. _MO{axis}={mo}, TS={ts}, SC={sc}, TE={te}, TA(OR)={ta}, TC={io.tc_text()}"
        )

def get_ts_bits(io: GalilIO, axis: str) -> dict:
    """Parse TS bits for axis status"""
    v = io.ts(axis)  # already int via float->int
    return {
        "in_motion":        (v >> 7) & 1,
        "err_limit":        (v >> 6) & 1,
        "motor_off":        (v >> 5) & 1,
        "fwd_lim_inactive": (v >> 3) & 1,   # 1=inactive, 0=active (CN dependent)
        "rev_lim_inactive": (v >> 2) & 1,
        "home":             (v >> 1) & 1,
        "latch":            (v >> 0) & 1,
        "_raw": v,
    }

def test_move_abs(io: GalilIO, axis: str, target_abs: int, sp=5000, ac=25000, dc=25000) -> Tuple[int,int]:
    """Test absolute move with proper error handling"""
    axis = axis.upper()
    safe_enable(io, axis)
    io.sp(axis, sp)
    io.ac(axis, ac)
    io.dc(axis, dc)
    io.pa(axis, target_abs)
    io.bg(axis)
    io.am(axis)
    pos = io.tp(axis)
    err = abs(pos - target_abs)
    return pos, err

def discover_axes(io: GalilIO, letters="ABCD") -> list:
    """Discover which axes are present"""
    present = []
    for a in letters:
        try:
            p = io.tp(a)              # TPA
            present.append(a)
            print(f"Axis {a}: Present - Position: {p}")
        except Exception:
            print(f"Axis {a}: TP failed; TC={io.tc_text()}")
    return present

def verify_servo_enable(io: GalilIO, axes):
    """Verify servo enable functionality"""
    for a in axes:
        try:
            safe_enable(io, a)
            ts = get_ts_bits(io, a)
            if ts["motor_off"]:
                raise RuntimeError(f"TS says motor_off after SH{a}")
            print(f"Axis {a}: Servo enabled successfully")
        except Exception as e:
            print(f"Axis {a}: Servo enable failed: {e}")

def run_motion_suite(io: GalilIO, axes, offset=100, profiles=None):
    """Run motion testing suite"""
    if profiles is None:
        profiles = [(5000, 25000, 25000), (20000, 200000, 200000)]
    results = {}
    for a in axes:
        results[a] = []
        base = io.tp(a)
        for sp, ac, dc in profiles:
            target = base + offset
            try:
                pos, err = test_move_abs(io, a, target, sp=sp, ac=ac, dc=dc)
                ok = (err <= 5)
                results[a].append({"sp":sp,"ac":ac,"dc":dc,"pos":pos,"err":err,"pass":ok})
                print(f"Axis {a}: Motion test {'PASSED' if ok else 'FAILED'} - Error: {err} counts")
            except Exception as e:
                results[a].append({"sp":sp,"ac":ac,"dc":dc,"error":str(e),"pass":False})
                print(f"Axis {a}: Motion test ERROR: {e}")
    return results

def teardown_axes(io: GalilIO, axes, power_off=True):
    """Teardown axes to safe positions"""
    for a in axes: 
        io.pa(a, 0)
    for a in axes: 
        io.bg(a)
    for a in axes: 
        io.am(a)
    if power_off:
        for a in axes: 
            io.mo(a)

def sanity_probe(io: GalilIO):
    """Run sanity probe with proper error handling"""
    try:
        print("ID:", io.id())
        print("TB:", io.tb())
        print("_BV:", io.bv())
        # quick A-axis poke
        try:
            safe_enable(io, "A")
            print("SHA OK, TPA =", io.tp("A"))
        except Exception as e:
            print("SHA failed:", e)
    except Exception as e:
        print("Sanity probe failed:", e)
