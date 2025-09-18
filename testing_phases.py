# testing_phases.py
# Comprehensive testing phases with proper axis classification

from diag_axis import AxisInfo, read_motor_type, classify_mode, safe_enable_if_needed
from motion_generic import move_absolute_and_check

def phase_axis_discovery(io, axes="ABCD"):
    """Discover which axes are present"""
    found = []
    for a in axes:
        try:
            p = io.tp(a)   # if TP works, the axis exists in the controller map
            print(f"[DISC] Axis {a}: Present - Position: {p}")
            found.append(a)
        except Exception:
            print(f"[DISC] Axis {a}: TP failed; TC={io.tc_text()}")
    return found

def phase_servo_enable(io, active_axes):
    """Enable servos where valid, handle steppers properly"""
    infos = []
    for a in active_axes:
        mt = read_motor_type(io, a)
        mode = classify_mode(mt)
        ok, note = safe_enable_if_needed(io, a, mode)
        info = AxisInfo(axis=a, mode=mode, mt_raw=mt, enabled=ok, note=note)
        if not ok:
            print(f"[ENABLE] {a}: FAIL - {note}")
        else:
            print(f"[ENABLE] {a}: OK   - {note} (MT={mt})")
        infos.append(info)
    return infos

def phase_motion(io, infos, distance=100, profiles=None, tol=5):
    """Test motion on all axes (servo and stepper)"""
    if profiles is None:
        profiles = [(5000, 25000, 25000), (20000, 200000, 200000)]
    results = {}
    for info in infos:
        a = info.axis
        # You can still move steppers without SH; for servo we prefer SH but we already handled enable outcome.
        try:
            base = io.tp(a)
            results[a] = []
            for sp, ac, dc in profiles:
                target = base + distance
                pos, err, passed = move_absolute_and_check(io, a, target, sp, ac, dc, tol)
                results[a].append(dict(sp=sp, ac=ac, dc=dc, pos=pos, err=err, passed=passed))
                print(f"[MOVE] {a}: target {target}, pos {pos}, |err| {err} -> {'PASS' if passed else 'FAIL'}")
        except Exception as e:
            tc = io.tc_text()
            print(f"[MOVE] {a}: ERROR {e} (TC={tc})")
            results[a] = [{"error": str(e), "tc": tc, "passed": False}]
    return results

def phase_teardown(io, active_axes):
    """Return axes to safe positions and power down"""
    print("[TEARDOWN] Returning axes to safe positions...")
    for a in active_axes: 
        io.pa(a, 0)
    for a in active_axes: 
        io.bg(a)
    for a in active_axes: 
        io.am(a)
    for a in active_axes:
        try: 
            io.mo(a)
        except: 
            pass
    print("[TEARDOWN] All axes returned to safe positions")

def run_full_test(io):
    """Run complete test sequence with proper error handling"""
    print("[SETUP] Echo off; clearing latched amp errors.")
    try: 
        io.cmd("EO 0")
    except: 
        pass
    try: 
        io.clear_amp_latched()
    except: 
        pass

    print("[SANITY] ID:", io.id())
    print("[SANITY] TB:", io.tb(), " _BV:", io.bv())

    print("[PHASE] Axis Discovery")
    active = phase_axis_discovery(io, "ABCD")
    if not active:
        print("[ABORT] No axes present.")
        return {"error": "No axes present"}

    print("[PHASE] Servo Enable (skips for steppers)")
    infos = phase_servo_enable(io, active)

    print("[PHASE] Motion")
    results = phase_motion(io, infos, distance=100, profiles=[(5000,25000,25000)], tol=5)

    print("[PHASE] Teardown: return to 0 and MO")
    phase_teardown(io, active)

    # Summary
    total = sum(1 for a in results for r in results[a] if r.get("passed"))
    print(f"[SUMMARY] {total}/{len(active)} axes had at least one passing profile.")
    
    return {
        "active_axes": active,
        "axis_infos": infos,
        "motion_results": results,
        "summary": f"{total}/{len(active)} axes passed motion test"
    }
