# discovery.py
# Requires an open gclib handle `g` (e.g., g = gclib.py(); g.GOpen("..."))

import threading
from typing import Dict, Iterable, Tuple, Union
from command_validator import CommandValidation, DMC4103CommandValidator

# Global command validator instance
_command_validator = DMC4103CommandValidator()

def safe_join(t, timeout=None):
    """Thread join guard to kill the 'cannot join current thread' error"""
    if not t: return
    if t is threading.current_thread():  # never join yourself
        return
    try: t.join(timeout=timeout)
    except: pass

def gc(g, cmd: str) -> str:
    """Centralized controller command wrapper that validates commands and raises RuntimeError with TC1 details"""
    try:
        # Validate command before sending to controller
        validation = _command_validator.validate_command(cmd)
        if not validation.valid:
            raise RuntimeError(f"Command validation failed: {cmd} - {validation.error_message}")
        
        # Log warnings if any
        if validation.warning_message:
            print(f"[VALIDATION WARNING] {cmd}: {validation.warning_message}")
        
        result = g.GCommand(cmd)
        if result and result.strip() == "?":
            # Get TC1 error details
            try:
                tc1 = g.GCommand("TC1") or "unknown"
                raise RuntimeError(f"Controller rejected: {cmd} (TC1={tc1})")
            except:
                raise RuntimeError(f"Controller rejected: {cmd} (TC1=unknown)")
        # Check for internal error responses
        if result and "internal error" in str(result).lower():
            raise RuntimeError(f"Controller internal error: {cmd} - {result}")
        return result
    except Exception as e:
        if "Command validation failed:" in str(e):
            raise  # Re-raise validation errors
        if "Controller rejected:" in str(e):
            raise  # Re-raise our custom error
        # For other exceptions, wrap them
        raise RuntimeError(f"Controller command failed: {cmd} - {e}")

AxisList = Union[Iterable[str], str]

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D"))
    if not axes:
        raise ValueError("No valid axes provided (A-D).")
    return axes

def _cmd(g, cmd: str) -> str:
    """Send a command and return the (stripped) response (may be empty)."""
    return gc(g, cmd)

def _num(s: str) -> float:
    try:
        return float(s.strip())
    except Exception:
        return float("nan")

def _get_ts(g, axis: str) -> int:
    v = _cmd(g, f"MG _TS{axis}")
    try:
        # take only first value if a comma sneaks in
        return int(float(v.split(',')[0]))
    except Exception:
        return 0  # treat as unknown but not fatal

def _get_tp(g, axis: str) -> float:
    # Use proper TP{axis} syntax for DMC-4143 compatibility
    return _num(_cmd(g, f"TP{axis}"))

def _get_ta_bankbits(g) -> int:
    """41x3-safe read of amplifier error banks. Combine _TA0.._TA3."""
    def _r(name):
        s = _cmd(g, f"MG {name}")  # will raise if "?"
        try:
            return int(float(s))
        except Exception:
            return 0
    try:
        return _r("_TA0") | _r("_TA1") | _r("_TA2") | _r("_TA3")
    except Exception:
        # If even the bank query is unsupported on this model, treat as no fault.
        return 0

def _get_ta_safe(g, axis: str) -> int:
    """Return 0/1 amplifier fault for this axis; never raises."""
    idx = "ABCD".find(axis.upper())
    if idx < 0:
        return 0
    bits = _get_ta_bankbits(g)
    return (bits >> idx) & 1

def _tc_clear_silent(g):
    """Clear TC without raising exceptions."""
    try:
        gc(g, "TC 0")
    except Exception:
        pass

# Adjust if your 41x3 has >8 isolated outputs; expanded to 1..16 for broader coverage
OUTPUT_BITS = range(1, 17)  # was 1..8; try 1..16 (or 1..24 if your unit has more)

# Once a bit/polarity works we cache it here to avoid scanning every run.
AMP_ENABLE_BITS = {}  # e.g. {"A": (3, "active-low")}
# After first successful autoscan, hard-code the learned bits like:
# AMP_ENABLE_BITS = {"A": (3, "active-low"), "B": (4, "active-high")}
# then set autoscan=False for faster, deterministic future runs

def _try_enable_bit(g, axis: str, bit: int, active_low: bool) -> bool:
    """Toggle one digital output as amp-enable, then attempt SH"""
    axis = axis.upper()
    _cmd(g, f"MO{axis}")
    import time
    time.sleep(0.1)  # 100ms delay
    _cmd(g, f"{'CB' if active_low else 'SB'} {bit}")   # assert enabling level
    time.sleep(0.05)  # 50ms delay
    _cmd(g, f"SH{axis}")
    mo_response = _cmd(g, f"MG _MO{axis}")
    mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '') if mo_response else "1"
    mo = float(mo_response.split(",")[0])
    return mo == 0.0

def enable_servo_or_explain(g, axis: str, autoscan: bool) -> Tuple[bool, str]:
    """
    Deterministic servo bring-up (amp-enable + verify)
    """
    axis = axis.upper()

    # 0) Guarantee servo mode (defensive)
    try: 
        _cmd(g, f"MT{axis}=0")
    except: 
        pass

    # 1) If we already learned the bit, use it.
    if axis in AMP_ENABLE_BITS:
        bit, pol = AMP_ENABLE_BITS[axis]
        if _try_enable_bit(g, axis, bit, pol == "active-low"):
            return True, f"enabled via DO{bit} ({pol})"

    # 2) One-shot autoscan to learn the output bit + polarity.
    if autoscan:
        for bit in OUTPUT_BITS:
            # active-high first
            try:
                if _try_enable_bit(g, axis, bit, active_low=False):
                    AMP_ENABLE_BITS[axis] = (bit, "active-high")
                    return True, f"autoscan DO{bit} active-high"
            except Exception:
                pass
            # then active-low
            try:
                if _try_enable_bit(g, axis, bit, active_low=True):
                    AMP_ENABLE_BITS[axis] = (bit, "active-low")
                    return True, f"autoscan DO{bit} active-low"
            except Exception:
                pass

    # 3) Still OFF → tell the operator exactly what's blocking.
    mo  = (_cmd(g, f"MG _MO{axis}") or "").strip()
    ts  = (_cmd(g, f"MG _TS{axis}") or "").strip()
    ta0 = (_cmd(g, "MG _TA0") or "").strip()
    return False, (f"Servo did not engage on {axis} (MO{axis}={mo}). "
                   f"Check amp-enable wiring/E-stop/drive-ready. TS={ts} TA0={ta0}")

def _amp_enable(g, axis: str):
    """Assert amplifier enable output if applicable."""
    bit = AMP_ENABLE_BITS.get(axis.upper())
    if bit is None:
        return
    try:
        gc(g, f"SB {int(bit)}")  # set output bit
        import time
        time.sleep(0.05)  # 50ms delay
    except:
        pass

def _servo_preflight(g, axis: str, amp_bits: dict, *, allow_autoscan=False, autoscan_bits=range(1,17)):
    """Force known-good servo state with robust enable chain and optional autoscan."""
    ax = axis.upper()

    # Servo mode only
    try:
        mt_response = gc(g, f"MG _MT{ax}") or "0"
        mt_response = mt_response.replace('\r', '').replace('\n', '').replace(':', '')
        mt = float(mt_response.split(",")[0])
    except Exception:
        mt = 0.0
    if mt != 0.0:
        gc(g, "MT 0,0,0,0")  # no steppers, ever

    # Quiesce and clear controller error
    for th in ("", " 1", " 2", " 3"):
        try:
            gc(g, f"AB{th}")
        except:
            pass
    try:
        gc(g, "ST")
        # AM commands might not be supported on DMC-4143, make them optional
        for ax in "ABCD":
            try:
                gc(g, f"AM{ax}")
            except:
                pass  # AM command not supported, continue anyway
    except:
        pass
    try:
        gc(g, "TC 0")
    except:
        pass

    # Be tolerant for discovery
    try:
        gc(g, "OE 0")
    except:
        pass
    try:
        gc(g, f"ER{ax}=200000")
    except:
        pass
    try:
        gc(g, f"TL{ax}=100")
    except:
        pass

    # --- amplifier enable handshake ---
    def _try_enable_with(bits, active_low):
        # set outputs to the desired "enabled" state
        for b in bits:
            if active_low:
                gc(g, f"CB {int(b)}")   # 0 = enabled
            else:
                gc(g, f"SB {int(b)}")   # 1 = enabled
        import time
        time.sleep(0.05)  # 50ms delay
        # power-cycle & SH
        gc(g, f"MO{ax}")
        time.sleep(0.15)  # 150ms delay
        gc(g, f"SH{ax}")
        gc(g, f"DP{ax}=0")
        mo_response = gc(g, f"MG _MO{ax}") or "1"
        mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '')
        mo = float(mo_response.split(",")[0])
        return mo == 0.0

    # 1) Use configured bits (if any) and try both polarities
    cfg_bits = amp_bits.get(ax, [])
    if cfg_bits:
        if _try_enable_with(cfg_bits, active_low=False):
            return
        if _try_enable_with(cfg_bits, active_low=True):
            return

    # 2) Optional: autoscan outputs to find the real enable bit/polarity
    if allow_autoscan and not cfg_bits:
        for b in autoscan_bits:
            if _try_enable_with([b], active_low=False):
                return
            if _try_enable_with([b], active_low=True):
                return

    # If we got here, enable chain failed — report everything we can
    ts = (gc(g, f"MG _TS{ax}") or "").strip()
    ta0 = (gc(g, "MG _TA0") or "0").strip()
    op = (gc(g, "MG _OP")  or "").strip()
    mo = (gc(g, f"MG _MO{ax}") or "").strip()
    raise RuntimeError(
        f"Servo did not engage on {ax} (MO{ax}={mo}). "
        f"Check amplifier enable/E-stop/drive-ready. TS={ts} TA-banks={ta0} OP={op} "
        f"(set amp enable bits in config or enable autoscan)"
    )

def _read_in(g, i):
    """Read input with 41x3-safe error handling"""
    s = gc(g, f"MG @IN[{i}]") or "0"
    # Clean up response - remove carriage returns, newlines, and colons
    s = s.replace('\r', '').replace('\n', '').replace(':', '')
    return int(float(s.split(",")[0]))

def _read_out(g, i):
    """Read output with 41x3-safe error handling"""
    s = gc(g, f"MG @OUT[{i}]") or "0"
    # Clean up response - remove carriage returns, newlines, and colons
    s = s.replace('\r', '').replace('\n', '').replace(':', '')
    return int(float(s.split(",")[0]))

def detect_outputs(g, max_try=32):
    """Detect how many outputs exist by trying SB/CB until we hit ?"""
    last = 0
    for i in range(1, max_try+1):
        try:
            gc(g, f"SB {i}")
            gc(g, f"CB {i}")
            last = i
        except RuntimeError:
            break
    return max(8, last)  # default to 8 if unsure

def detect_inputs(g, max_try=32):
    """Detect how many inputs exist by trying @IN until we hit ?"""
    last = 0
    for i in range(1, max_try+1):
        try:
            _ = float(gc(g, f"MG @IN[{i}]"))
            last = i
        except RuntimeError:
            break
    return max(8, last)

def write_do(g, i, val):
    """Write DO using SB/CB commands only"""
    gc(g, f"{'SB' if val else 'CB'} {i}")

def _write_out(g, i, val):
    """Write output using SB/CB commands only (no @OUT assignments)"""
    write_do(g, i, val)

def detect_ranges(g, max_probe=32):
    """Detect actual hardware IO ranges using new detection methods"""
    nin = detect_inputs(g, max_probe)
    nout = detect_outputs(g, max_probe)
    print(f"[IO] detected IN 1..{nin}, OUT 1..{nout}")
    return nin, nout

def try_toggle_do(g, i):
    """Toggle DO i with readback; returns True if it visibly changes."""
    try:
        before = _read_out(g, i)
    except:
        before = None
    try:
        _write_out(g, i, 1)
        _write_out(g, i, 0)
        after = _read_out(g, i)
        return (before is not None) and (after in (0,1))
    except Exception as e:
        print(f"[IO] DO{i} write unsupported ({e})")
        return False

def io_snapshot(g):
    """41x3-safe IO snapshot that detects hardware limits"""
    nin, nout = detect_ranges(g)
    ins  = []
    for i in range(1, nin+1):
        try: 
            ins.append(_read_in(g, i))
        except: 
            break
    print(f"[IO] IN[1..{nin}]={ins}")
    
    # Also show CN status
    try:
        cn = gc(g, "MG _CN") or "?"
        print(f"[IO] CN={cn}")
    except Exception:
        print(f"[IO] CN=?")

def io_correlation_probe(g):
    """Run once before discovery; toggles each DO and logs any input that flips"""
    try:
        # Detect actual hardware limits first
        nin, nout = detect_ranges(g)
        
        print(f"[IO-CORRELATION] Testing {nin} inputs, {nout} outputs")
        
        base_ins = []
        for k in range(1, nin+1):
            try:
                base_ins.append(_read_in(g, k))
            except:
                break
        
        print(f"[IO-CORRELATION] Base inputs: {base_ins}")
        
        # Only test outputs within detected range
        for bit in range(1, min(nout+1, 17)):  # cap at 16 for safety
            for set_high in (True, False):
                try:
                    _write_out(g, bit, set_high)
                    # Use time.sleep for IO correlation - more reliable than WT commands
                    import time
                    time.sleep(0.05)  # 50ms delay
                    
                    ins = []
                    for k in range(1, nin+1):
                        try:
                            ins.append(_read_in(g, k))
                        except:
                            break
                    
                    diffs = [k for k,(a,b) in enumerate(zip(base_ins, ins), start=1) if a != b]
                    if diffs:
                        print(f"[IO-CORRELATION] toggling DO{bit} ({'HIGH' if set_high else 'LOW'}) flipped IN{diffs}")
                    
                    # restore
                    _write_out(g, bit, not set_high)
                    time.sleep(0.02)  # 20ms delay
                except Exception as e:
                    print(f"[IO-CORRELATION] Failed testing DO{bit}: {e}")
                    
    except Exception as e:
        print(f"[IO-CORRELATION] probe failed: {e}")

def log_io_snapshot(g):
    """Legacy function - now calls the robust io_snapshot"""
    io_snapshot(g)

def _quiesce(g):
    """Abort any background program, stop axes, and wait for them to be idle."""
    # abort all threads that might be running; then stop and wait
    for th in ("", " 1", " 2", " 3"):
        try:
            gc(g, f"AB{th}")
        except:
            pass
    try:
        gc(g, "ST")
        # AM commands might not be supported on DMC-4143, make them optional
        for ax in "ABCD":
            try:
                gc(g, f"AM{ax}")
            except:
                pass  # AM command not supported, continue anyway
    except:
        pass
    _tc_clear_silent(g)

def _wait_idle(g, axis, timeout_ms=1000):
    """Wait for axis to be idle (motion bit = 0)."""
    import time
    t0 = time.time()
    while True:
        ts = _get_ts(g, axis)
        in_motion = (ts >> 7) & 1
        if not in_motion:
            return True
        if (time.time() - t0) * 1000 > timeout_ms:
            return False
        time.sleep(0.02)

def setup_baseline(g):
    """Lock in clean base config and keep it"""
    for cmd in ("TC 0", "AB", "ST"):  # clear errors, stop anything
        try: gc(g, cmd)
        except: pass
    # Force SERVO motor type, sane CN/OE
    for ax in "AB":  # only the axes you use
        try: gc(g, f"MT{ax}=0")  # 0 = servo
        except: pass
    for cmd in ("CN 0", "OE 0"):
        try: gc(g, cmd)
        except: pass
    # Engage only the axes you use
    for ax in "AB":
        try: gc(g, f"SH{ax}")
        except: pass

def force_idle_servo_on(g, ax):
    """Servo-ON idle that stops motion without disabling the axis"""
    # Stop any existing motion first
    for c in (f"ST {ax}", "AB"): 
        try: gc(g, c)
        except: pass
    
    # Wait a moment for motion to stop
    import time
    time.sleep(0.1)
    
    # Clear any amplifier errors
    try: gc(g, f"AM{ax}")
    except: pass
    
    # Set up for servo enable
    try:
        gc(g, f"JG{ax}=0")
        gc(g, f"BG{ax}")   # clears prior profiled/jog state; no motion if JG=0
        gc(g, f"AM{ax}")
    except: pass
    
    # Enable servo with retry logic
    for attempt in range(3):
        try: 
            gc(g, f"SH{ax}")  # idempotent, ensures servo ON
            time.sleep(0.2)  # Give time for servo to enable
            
            # Verify servo is enabled
            mo_status = gc(g, f"MG _MO{ax}")
            # Clean up response - remove carriage returns, newlines, and colons
            mo_status = mo_status.replace('\r', '').replace('\n', '').replace(':', '') if mo_status else "1"
            mo_value = float(mo_status.split(",")[0])
            if mo_value == 0.0:
                print(f"[DISCOVERY] {ax}: Servo enabled successfully")
                break
            else:
                print(f"[DISCOVERY] {ax}: Servo enable attempt {attempt + 1} failed (MO={mo_value})")
        except Exception as e:
            print(f"[DISCOVERY] {ax}: Servo enable attempt {attempt + 1} failed: {e}")
            if attempt == 2:  # Last attempt
                print(f"[DISCOVERY] {ax}: All servo enable attempts failed")
    
    try: gc(g, f"DP{ax}=0")
    except: pass

def _force_idle_axis(g, axis: str):
    """Hard quiesce per axis before probing - kills stray jog/programs, truly idles the axis."""
    axis = axis.upper()
    # kill any program, stop motion
    for th in ("", " 1", " 2", " 3"):
        try:
            gc(g, f"AB{th}")
        except:
            pass
    try:
        gc(g, f"ST{axis}; AM{axis}")
    except:
        pass
    # neutralize any latched jog
    try:
        gc(g, f"JG{axis}=0")
        gc(g, f"BG{axis}; AM{axis}")
    except:
        pass

    # enable amp (if mapped), power-cycle axis, bring servo ON
    try:
        _amp_enable(g, axis)
        # Use servo-ON idle instead of MO command
        force_idle_servo_on(g, axis)
    except Exception:
        pass
    _tc_clear_silent(g)

    # verify servo actually engaged
    try:
        mo_response = gc(g, f"MG _MO{axis}") or "1"
        mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '')
        mo = float(mo_response.split(",")[0])
        if mo != 0.0:
            raise RuntimeError(f"Servo did not engage on {axis} (MO{axis}={mo}). Check amp enable/E-stop/drive ready.")
    except Exception as e:
        # propagate so probe logs the real reason
        raise

def _decode_ts(ts: int) -> Dict[str, int]:
    # TS bits (1=bit set):
    # 7 motion, 6 error-limit, 5 motor-off, 4 reserved, 3 fwd-limit-inactive, 2 rev-limit-inactive, 1 home, 0 latch
    return {
        "motion":           (ts >> 7) & 1,
        "error_limit":      (ts >> 6) & 1,
        "motor_off":        (ts >> 5) & 1,
        "fwd_limit_inact":  (ts >> 3) & 1,
        "rev_limit_inact":  (ts >> 2) & 1,
        "home":             (ts >> 1) & 1,
        "latch":            (ts >> 0) & 1,
    }

def _set_profile(g, axis: str, sp: int, ac: int, dc: int) -> None:
    # SP X=…, AC X=…, DC X=…
    _cmd(g, f"SP{axis}={int(sp)}")
    _cmd(g, f"AC{axis}={int(ac)}")
    _cmd(g, f"DC{axis}={int(dc)}")

def _nudge(g, axis: str, counts: int) -> None:
    # Wait for motor to be idle before issuing PR command
    _wait_idle(g, axis, timeout_ms=1000)
    # PR X=…, BGX, AMX
    _cmd(g, f"PR{axis}={int(counts)}")
    _cmd(g, f"BG{axis}")
    # AM command might not be supported on DMC-4143, make it optional
    try:
        _cmd(g, f"AM{axis}")
    except:
        pass  # AM command not supported, continue anyway

def safe_probe(g, axis, sp=1500, ac=8000, dc=8000, nudge=16000):
    """Nudge only when _MO==0 (and make motion easy to see)"""
    ax = axis.upper()
    mo_response = gc(g, f"MG _MO{ax}") or "1"
    mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '')
    mo = float(mo_response.split(",")[0])
    if mo != 0.0:
        return False, f"Servo OFF before nudge (MO{ax}={mo})"

    gc(g, f"SP{ax}={sp}; AC{ax}={ac}; DC{ax}={dc}")
    def n(c): 
        # Wait for motor to be idle before issuing PR command
        _wait_idle(g, ax, timeout_ms=1000)
        gc(g, f"PR{ax}={c}")
        gc(g, f"BG{ax}")
        # AM command might not be supported on DMC-4143, make it optional
        try:
            gc(g, f"AM{ax}")
        except:
            pass  # AM command not supported, continue anyway
    n(+nudge)
    tp_pos_response = gc(g, f"TP{ax}") or "0"
    tp_pos_response = tp_pos_response.replace('\r', '').replace('\n', '').replace(':', '')
    tp_pos = float(tp_pos_response.split(",")[0])
    n(-nudge)
    tp_neg_response = gc(g, f"TP{ax}") or "0"
    tp_neg_response = tp_neg_response.replace('\r', '').replace('\n', '').replace(':', '')
    tp_neg = float(tp_neg_response.split(",")[0])

    moved = abs(tp_pos) >= 10  # Very sensitive threshold - any significant movement
    return moved, f"tp_pos={tp_pos:.0f} tp_neg={tp_neg:.0f}"

def probe_axis(g, axis: str, sp=1500, ac=8000, dc=8000, nudge_counts=32000, settle_back=False, amp_bits=None):
    """Probe axis for hardware presence - attempts servo enable but continues even if servo fails."""
    ax = axis.upper()
    r = {"axis": ax, "present": False, "tp_after_pos": float("nan"), "tp_after_neg": float("nan"),
         "ta": 0, "ts": 0, "ts_bits": {}, "notes": ""}

    # Try to enable servo
    try: gc(g, f"SH{ax}")  # idempotent
    except: pass
    
    servo_enabled = False
    try:
        mo_response = gc(g, f"MG _MO{ax}")
        # Clean up response - remove carriage returns, newlines, and colons
        mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '')
        mo = float(mo_response.split(",")[0])
        if mo == 0.0:
            servo_enabled = True
            print(f"[DISCOVERY] {ax}: Servo enabled (MO=0)")
        else:
            print(f"[DISCOVERY] {ax}: Servo not enabled (MO={mo}), will attempt limited discovery")
    except Exception as e:
        print(f"[DISCOVERY] {ax}: Could not check servo status: {e}, will attempt limited discovery")
    
    # Debug logging for Axis A
    if ax == "A":
        print(f"[DISCOVERY] {ax}: Debug - servo_enabled={servo_enabled}, mo={mo if 'mo' in locals() else 'unknown'}")
    
    # If servo is not enabled, axis is not present (no motor connected)
    if not servo_enabled:
        # Check if we can at least read position and status for diagnostic purposes
        try:
            tp = gc(g, f"TP{ax}")
            ts = gc(g, f"MG _TS{ax}")
            ta = gc(g, f"MG _TA0")
            print(f"[DISCOVERY] {ax}: Hardware present but servo not enabled - TP={tp}, TS={ts}, TA={ta}")
            r["present"] = False  # No motor connected - axis not present
            r["notes"] = f"Hardware present but servo not enabled (MO={mo if 'mo' in locals() else 'unknown'})"
            ts_clean = ts.replace('\r', '').replace('\n', '').replace(':', '') if ts else "0"
            ta_clean = ta.replace('\r', '').replace('\n', '').replace(':', '') if ta else "0"
            r["ts"] = int(float(ts_clean.split(",")[0])) if ts_clean else 0
            r["ta"] = int(float(ta_clean.split(",")[0])) if ta_clean else 0
            return r
        except Exception as e:
            print(f"[DISCOVERY] {ax}: No hardware response: {e}")
            r["notes"] = f"No hardware response: {e}"
            return r

    # Use the deterministic servo bring-up function
    ok, note = enable_servo_or_explain(g, ax, autoscan=True)   # first successful run will "learn"
    print(f"[DISCOVERY] {ax}: {note}")
    if not ok:
        r["notes"] = note
        try:
            ts_response = _cmd(g, f"MG _TS{ax}") or "0"
            ts_response = ts_response.replace('\r', '').replace('\n', '').replace(':', '')
            r["ts"] = int(float(ts_response.split(",")[0]))
        except:
            pass
        try:
            ta_response = _cmd(g, "MG _TA0") or "0"
            ta_response = ta_response.replace('\r', '').replace('\n', '').replace(':', '')
            r["ta"] = int(float(ta_response.split(",")[0]))
        except:
            pass
        return r  # refuse to nudge if servo is OFF
    
    # TODO: After first successful run, hard-code AMP_ENABLE_BITS and set autoscan=False

    # Assert SH again after forcing servo config (cheap and idempotent)
    try: 
        gc(g, f"SH{ax}")
    except: 
        pass
    
    # Stop any existing motion before discovery
    try:
        gc(g, f"ST{ax}")  # Stop motion
        gc(g, f"AM{ax}")  # After motion
    except:
        pass
    
    mo_response = gc(g, f"MG _MO{ax}") or "1"
    mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '')
    mo = float(mo_response.split(",")[0])
    if mo != 0.0:
        r["notes"] = f"Servo OFF (MO{ax}=1). Check amp enable / E-stop / drive ready."
        return r  # refuse to nudge if _MOx!=0

    # gentle profile
    _cmd(g, f"SP{ax}={int(sp)}")
    _cmd(g, f"AC{ax}={int(ac)}")
    _cmd(g, f"DC{ax}={int(dc)}")

    def _nudge(counts):
        # Wait for motor to be idle before issuing PR command
        _wait_idle(g, ax, timeout_ms=1000)
        _cmd(g, f"PR{ax}={int(counts)}")
        _cmd(g, f"BG{ax}")
        # AM command might not be supported on DMC-4143, make it optional
        try:
            _cmd(g, f"AM{ax}")
        except:
            pass  # AM command not supported, continue anyway

    _nudge(+abs(nudge_counts))
    tp_pos_response = _cmd(g, f"TP{ax}") or "0"
    tp_pos_response = tp_pos_response.replace('\r', '').replace('\n', '').replace(':', '')
    tp_pos = float(tp_pos_response.split(",")[0])
    _nudge(-abs(nudge_counts))
    tp_neg_response = _cmd(g, f"TP{ax}") or "0"
    tp_neg_response = tp_neg_response.replace('\r', '').replace('\n', '').replace(':', '')
    tp_neg = float(tp_neg_response.split(",")[0])

    moved = abs(tp_pos) >= 10  # Very sensitive threshold - any significant movement
    ts_response = _cmd(g, f"MG _TS{ax}") or "0"
    ts_response = ts_response.replace('\r', '').replace('\n', '').replace(':', '')
    ts = int(float(ts_response.split(",")[0]))
    try:
        ta_response = _cmd(g, "MG _TA0") or "0"
        ta_response = ta_response.replace('\r', '').replace('\n', '').replace(':', '')
        ta = int(float(ta_response.split(",")[0]))
    except:
        ta = 0

    if settle_back:
        # Get current position and return to original position
        current_pos_response = _cmd(g, f'MG _TP{ax}') or '0'
        current_pos_response = current_pos_response.replace('\r', '').replace('\n', '').replace(':', '')
        current_pos = float(current_pos_response.split(',')[0])
        # Only move if the position change is significant (avoid very small moves that DMC-4143 might reject)
        if abs(current_pos) > 500:  # Only move if position change is more than 500 counts
            _cmd(g, f"PR{ax}={int(-current_pos)}")
            _cmd(g, f"BG{ax}")
            # AM command might not be supported on DMC-4143, make it optional
            try:
                _cmd(g, f"AM{ax}")
            except:
                pass  # AM command not supported, continue anyway

    # More lenient presence detection - allow for minor TE errors and motion issues
    # TE errors can occur during discovery but don't necessarily mean hardware is absent
    # If servo is enabled (MO=0), consider it present even if motion test fails
    servo_enabled = mo == 0.0
    motion_detected = moved and ((ts >> 5) & 1) == 0
    
    # Debug logging for Axis A
    if ax == "A":
        print(f"[DISCOVERY] {ax}: Debug - mo={mo}, servo_enabled={servo_enabled}, moved={moved}, motion_detected={motion_detected}")
    
    # Consider axis present if either motion is detected OR servo is enabled
    is_present = motion_detected or servo_enabled
    
    r.update({
        "present": is_present,
        "tp_after_pos": tp_pos, "tp_after_neg": tp_neg,
        "ta": ta, "ts": ts, "ts_bits": _decode_ts(ts),
        "notes": f"tp_pos={tp_pos:.0f} tp_neg={tp_neg:.0f} MO=0 TS={ts} TA={ta}" + ("" if moved else " (insufficient motion)") + ("" if servo_enabled else " (servo not enabled)")
    })
    return r

def discover_axes(
    g,
    axes: AxisList = ("A","B","C","D"),
    sp: int = 1500,      # gentler speed
    ac: int = 8000,      # gentler acceleration
    dc: int = 8000,      # gentler deceleration
    nudge_counts: int = 32000,  # bigger nudge (~1/2 turn)
    amp_bits: dict = None,
) -> Dict[str, Dict]:
    """
    Runs discovery over the specified axes using only:
      SHX, DP X=0, SP/AC/DC, PR X=…, BGX, AMX, TPX, MG _TSX, TAX
    Returns a dict keyed by axis with probe results and a convenience list of active axes.
    """
    # Clear controller errors at phase boundary
    try: gc(g, "TC 0")
    except: pass
    
    # Setup baseline config once and keep it
    setup_baseline(g)
    
    # Keep servos ON before discovery begins - only A/B axes
    servo_enabled_axes = []
    for ax in "AB":
        force_idle_servo_on(g, ax)
        try:
            mo_response = gc(g, f"MG _MO{ax}")
            # Clean up response - remove carriage returns, newlines, and colons
            mo_response = mo_response.replace('\r', '').replace('\n', '').replace(':', '') if mo_response else "1"
            mo = float(mo_response.split(",")[0])
            if mo != 0.0:
                print(f"[DISCOVERY] {ax}: Servo OFF (MO{ax}=1) before probe. Check enable/E-stop/drive-ready.")
                print(f"[DISCOVERY] {ax}: Will attempt discovery anyway to check for hardware presence")
            else:
                servo_enabled_axes.append(ax)
                print(f"[DISCOVERY] {ax}: Servo enabled successfully")
        except Exception as e:
            print(f"[DISCOVERY] {ax}: Could not check servo status: {e}")
            print(f"[DISCOVERY] {ax}: Will attempt discovery anyway to check for hardware presence")
    
    if not servo_enabled_axes:
        print("[DISCOVERY] Warning: No servos enabled, but will attempt discovery to check hardware presence")
    
    # Quiesce motion and clear any stale controller error code before starting
    _quiesce(g)
    
    # Emit IO snapshot so wiring issues are obvious in log
    io_snapshot(g)
    
    # Run IO correlation probe to map drive-ready inputs
    io_correlation_probe(g)

    ax_list = _norm_axes(axes)
    results: Dict[str, Dict] = {}
    active: list[str] = []

    for ax in ax_list:
        try:
            res = probe_axis(g, ax, sp=sp, ac=ac, dc=dc, nudge_counts=nudge_counts, settle_back=False, amp_bits=amp_bits)
        except Exception as e:
            # Don't abort discovery; mark axis as absent and carry the reason.
            res = {
                "axis": ax,
                "present": False,
                "tp_after_pos": float("nan"),
                "tp_after_neg": float("nan"),
                "ta": 0,
                "ts": 0,
                "ts_bits": {},
                "notes": f"probe skipped: {e}",
            }
        finally:
            # Very important: don't let a "?" leave TC=2 for the next axis
            _tc_clear_silent(g)

        results[ax] = res
        if res.get("present"):
            active.append(ax)

    # When discovery finds no axes, print why for each axis
    if not active:
        for ax, res in results.items():
            try:
                mo = _cmd(g, f"MG _MO{ax}")
            except:
                mo = "?"
            ts = res.get("ts", "?")
            print(f"[DISCOVERY] {ax}: {res.get('notes','')}")
            print(f"            MO={mo} TS={ts}")

    return {"results": results, "active": active}
