# test_motion.py
# Requires an open gclib handle `g` (e.g., g = gclib.py(); g.GOpen("..."))
# Formatting honors your style:
#   - Begin motion:  BGA (no space)
#   - Absolute move: PA A=1000 (with space)
#   - Query pos:     TPA  (no space)
#   - Jog:           JGA=5000 (no space)

from typing import Dict, List, Iterable, Tuple, Union
import time

AxisList = Union[Iterable[str], str]

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D"))
    if not axes:
        raise ValueError("No valid axes (A-D).")
    return axes

def _cmd(g, cmd: str) -> str:
    r = g.GCommand(cmd)
    if isinstance(r, str):
        # Clean up response - remove carriage returns, newlines, and colons
        return r.replace('\r', '').replace('\n', '').replace(':', '').strip()
    return ""

def _num(s: str) -> float:
    try:
        return float(s.strip())
    except Exception:
        return float("nan")

def _tp(g, axis: str) -> float:
    return _num(_cmd(g, f"TP{axis}"))

def _set_profile(g, axis: str, sp: int, ac: int, dc: int) -> None:
    # SP A=…, AC A=…, DC A=…
    _cmd(g, f"SP{axis}={int(sp)}")
    _cmd(g, f"AC{axis}={int(ac)}")
    _cmd(g, f"DC{axis}={int(dc)}")

def _wait_for_motion_complete(g, axis: str, timeout: float = 10.0) -> None:
    """Wait for motion to complete by polling _BG operand"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if motion is still active using _BG operand
            bg_status = _cmd(g, f"MG _BG{axis}")
            if bg_status and bg_status != "?":
                # _BG returns 1 if motion is active, 0 if complete
                bg_value = float(bg_status.split(",")[0])
                if bg_value == 0.0:
                    return  # Motion complete
            time.sleep(0.1)  # Poll every 100ms
        except Exception:
            time.sleep(0.1)
    # If we get here, motion didn't complete in time
    print(f"Warning: Motion on axis {axis} did not complete within {timeout}s")

def _begin_and_wait(g, axis: str) -> None:
    _cmd(g, f"BG{axis}")
    # AM command is not valid in terminal, so poll for motion completion
    _wait_for_motion_complete(g, axis)

def _move_and_verify(g, axis: str, target: int, tol_counts: int) -> Dict[str, Union[float, int, bool]]:
    """
    Sequence:
      ST X (stop any existing motion)
      PA X=target
      BGX
      AMX
      TPA → error = |TPA - target|
      MG "..." and MG @ABS[...] for controller-side trace
    """
    # Stop any existing motion first
    try:
        print(f"[MOTION] {axis}: Stopping any existing motion...")
        _cmd(g, f"ST{axis}")
        _wait_for_motion_complete(g, axis)
        print(f"[MOTION] {axis}: Motion stopped successfully")
    except Exception as e:
        print(f"[MOTION] {axis}: Error stopping motion: {e}")
        pass
    
    # Announce from controller
    print(f"AX {axis} -> {target} BEGIN")

    # Absolute target and run
    _cmd(g, f"PA{axis}={int(target)}")
    _begin_and_wait(g, axis)

    # Measure
    tp = _tp(g, axis)
    err = abs(tp - target)
    passed = err <= tol_counts

    # Controller-side message including @ABS usage (as requested)
    # Example: MG "ERR:", @ABS[TPA-1000]
    print(f"AX {axis} DONE TPL={tp}")
    print(f"AX {axis} ERR={abs(tp - int(target))}")

    # Host-side result
    return {
        "axis": axis,
        "target": target,
        "tp": tp,
        "error": err,
        "pass": passed
    }

def optional_jog(g, axis: str, jg_speed: int = 5000, dwell_ms: int = 500) -> None:
    """
    Exercise velocity control briefly:
      JGX=<speed>, BGX, host sleep <ms>, STX, poll _BGX
    NOTE: WT is program-only (trippoint), use host sleep instead
    """
    _cmd(g, f"JG{axis}={int(jg_speed)}")  # e.g., JGA=5000
    _cmd(g, f"BG{axis}")
    time.sleep(dwell_ms / 1000.0)  # Host sleep, NOT WT command (WT is program-only)
    _cmd(g, f"ST{axis}")
    _wait_for_motion_complete(g, axis)
    print(f"AX {axis} JOG COMPLETE TPL={_tp(g, axis)}")

def run_simple_motion_test(g, axis: str, speed: int = 2000, distance: int = 50000) -> Dict[str, Union[float, int, bool, str]]:
    """
    Simple motion test for a single axis:
    1. Check if motor is present (servo enabled)
    2. Move +distance counts
    3. Return to 0
    4. Move -distance counts  
    5. Return to 0
    """
    print(f"=== SIMPLE MOTION TEST FOR AXIS {axis} ===")
    
    result = {
        "axis": axis,
        "motor_present": False,
        "test_passed": False,
        "moves_completed": 0,
        "final_position": 0.0,
        "notes": ""
    }
    
    try:
        # 1. Check if motor is present (servo enabled) and maintain servo status
        print(f"Axis {axis}: Checking for motor presence...")
        mo_status = _cmd(g, f"MG _MO{axis}")
        if mo_status and mo_status != "?":
            mo_value = float(mo_status.split(",")[0])
            if mo_value == 0.0:
                print(f"Axis {axis}: Motor detected (MO=0)")
                result["motor_present"] = True
            else:
                print(f"Axis {axis}: Servo not enabled (MO={mo_value}) - attempting to enable...")
                _cmd(g, f"SH{axis}")
                # Check again
                mo_check = _cmd(g, f"MG _MO{axis}")
                if mo_check and mo_check != "?":
                    mo_verify = float(mo_check.split(",")[0])
                    if mo_verify == 0.0:
                        print(f"Axis {axis}: Servo enabled successfully (MO=0)")
                        result["motor_present"] = True
                    else:
                        print(f"Axis {axis}: No motor connected (MO={mo_verify})")
                        result["notes"] = f"No motor connected (MO={mo_verify})"
                        return result
                else:
                    print(f"Axis {axis}: Cannot verify servo status")
                    result["notes"] = "Cannot verify servo status"
                    return result
        else:
            print(f"Axis {axis}: Cannot read servo status - attempting to enable...")
            _cmd(g, f"SH{axis}")
            # Check again
            mo_check = _cmd(g, f"MG _MO{axis}")
            if mo_check and mo_check != "?":
                mo_verify = float(mo_check.split(",")[0])
                if mo_verify == 0.0:
                    print(f"Axis {axis}: Servo enabled successfully (MO=0)")
                    result["motor_present"] = True
                else:
                    print(f"Axis {axis}: Cannot enable servo (MO={mo_verify})")
                    result["notes"] = f"Cannot enable servo (MO={mo_verify})"
                    return result
            else:
                print(f"Axis {axis}: Cannot verify servo status")
                result["notes"] = "Cannot verify servo status"
                return result
        
        # 2. Get starting position
        start_pos = _tp(g, axis)
        print(f"Axis {axis}: Starting position = {start_pos}")
        
        # 3. Set motion parameters
        print(f"Axis {axis}: Setting motion parameters...")
        _cmd(g, f"SP{axis}={speed}")
        _cmd(g, f"AC{axis}={speed * 2}")  # 2x speed for acceleration
        _cmd(g, f"DC{axis}={speed * 2}")  # 2x speed for deceleration
        
        # 3.5. Check controller status before motion
        print(f"Axis {axis}: Checking controller status...")
        tc_status = _cmd(g, "TC")
        if tc_status and tc_status != "?":
            tc_value = int(tc_status.split(",")[0])
            if tc_value != 0:
                print(f"Axis {axis}: Controller error detected (TC={tc_value}) - attempting to clear...")
                _cmd(g, "TC")  # Clear error
                time.sleep(0.1)
        
        # Check servo status again before motion
        mo_final = _cmd(g, f"MG _MO{axis}")
        if mo_final and mo_final != "?":
            mo_value = float(mo_final.split(",")[0])
            if mo_value != 0.0:
                print(f"Axis {axis}: Servo not enabled before motion (MO={mo_value}) - enabling...")
                _cmd(g, f"SH{axis}")
                time.sleep(0.1)
        
        # 4. Move +distance counts
        print(f"Axis {axis}: Moving +{distance} counts...")
        target_pos = start_pos + distance
        
        # Send position command
        pa_result = _cmd(g, f"PA{axis}={int(target_pos)}")
        if pa_result == "?":
            print(f"Axis {axis}: PA command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        # Send begin motion command
        bg_result = _cmd(g, f"BG{axis}")
        if bg_result == "?":
            print(f"Axis {axis}: BG command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        _wait_for_motion_complete(g, axis, timeout=30.0)
        
        # Check position
        pos1 = _tp(g, axis)
        print(f"Axis {axis}: Position after +{distance} move = {pos1}")
        result["moves_completed"] += 1
        
        # 5. Return to 0
        print(f"Axis {axis}: Returning to position 0...")
        pa_result = _cmd(g, f"PA{axis}=0")
        if pa_result == "?":
            print(f"Axis {axis}: PA command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        bg_result = _cmd(g, f"BG{axis}")
        if bg_result == "?":
            print(f"Axis {axis}: BG command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        _wait_for_motion_complete(g, axis, timeout=30.0)
        
        pos2 = _tp(g, axis)
        print(f"Axis {axis}: Position after return to 0 = {pos2}")
        result["moves_completed"] += 1
        
        # 6. Move -distance counts
        print(f"Axis {axis}: Moving -{distance} counts...")
        target_pos = -distance
        pa_result = _cmd(g, f"PA{axis}={int(target_pos)}")
        if pa_result == "?":
            print(f"Axis {axis}: PA command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        bg_result = _cmd(g, f"BG{axis}")
        if bg_result == "?":
            print(f"Axis {axis}: BG command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        _wait_for_motion_complete(g, axis, timeout=30.0)
        
        pos3 = _tp(g, axis)
        print(f"Axis {axis}: Position after -{distance} move = {pos3}")
        result["moves_completed"] += 1
        
        # 7. Return to 0
        print(f"Axis {axis}: Returning to position 0...")
        pa_result = _cmd(g, f"PA{axis}=0")
        if pa_result == "?":
            print(f"Axis {axis}: PA command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        bg_result = _cmd(g, f"BG{axis}")
        if bg_result == "?":
            print(f"Axis {axis}: BG command failed - checking controller status...")
            tc_status = _cmd(g, "TC")
            print(f"Axis {axis}: Controller status: TC={tc_status}")
            return result
        
        _wait_for_motion_complete(g, axis, timeout=30.0)
        
        final_pos = _tp(g, axis)
        print(f"Axis {axis}: Final position = {final_pos}")
        result["moves_completed"] += 1
        result["final_position"] = final_pos
        
        # 8. Determine if test passed (all 4 moves completed and reasonably close to 0)
        if result["moves_completed"] == 4 and abs(final_pos) < 100:  # Within 100 counts of 0
            result["test_passed"] = True
            result["notes"] = f"Test passed - all 4 moves completed, final position = {final_pos}"
            print(f"Axis {axis}: SIMPLE MOTION TEST PASSED")
        else:
            result["test_passed"] = False
            result["notes"] = f"Test failed - {result['moves_completed']}/4 moves completed, final position = {final_pos}"
            print(f"Axis {axis}: SIMPLE MOTION TEST FAILED")
        
    except Exception as e:
        print(f"Axis {axis}: Simple motion test error: {e}")
        result["notes"] = f"Test error: {e}"
        result["test_passed"] = False
    
    return result

def run_comprehensive_individual_axis_tests(
    g,
    axes: AxisList,
    test_speeds: List[int] = [1000, 2000, 5000],
    test_duration_seconds: int = 5,
    movement_distance: int = 10000,
) -> Dict[str, List[Dict[str, Union[float, int, bool, str]]]]:
    """
    Comprehensive individual axis testing:
    1. Check which axes have motors connected (servo enabled)
    2. For each axis with a motor, test individually:
       - Positive direction at different speeds
       - Negative direction at different speeds
       - Each movement runs for specified duration
    3. Test each axis one at a time to avoid interference
    """
    ax_list = _norm_axes(axes)
    summary: Dict[str, List[Dict[str, Union[float, int, bool, str]]]] = {}
    
    print("=== COMPREHENSIVE INDIVIDUAL AXIS TESTING ===")
    print(f"Testing {len(ax_list)} axes: {', '.join(ax_list)}")
    
    for axis in ax_list:
        print(f"--- Testing Axis {axis} ---")
        results: List[Dict[str, Union[float, int, bool, str]]] = []
        
        # Check if motor is connected (servo enabled)
        try:
            mo_status = _cmd(g, f"MG _MO{axis}")
            if mo_status and mo_status != "?":
                mo_value = float(mo_status.split(",")[0])
                if mo_value != 0.0:
                    print(f"Axis {axis}: No motor connected (MO={mo_value})")
                    results.append({
                        "axis": axis,
                        "test_type": "motor_detection",
                        "pass": False,
                        "notes": f"No motor connected (MO={mo_value})"
                    })
                    summary[axis] = results
                    continue
                else:
                    print(f"Axis {axis}: Motor detected (MO=0)")
            else:
                print(f"Axis {axis}: Cannot read servo status, attempting to enable")
                _cmd(g, f"SH{axis}")
                # Check again
                mo_check = _cmd(g, f"MG _MO{axis}")
                if mo_check and mo_check != "?":
                    mo_verify = float(mo_check.split(",")[0])
                    if mo_verify == 0.0:
                        print(f"Axis {axis}: Motor detected after enable (MO=0)")
                    else:
                        print(f"Axis {axis}: No motor connected (MO={mo_verify})")
                        results.append({
                            "axis": axis,
                            "test_type": "motor_detection",
                            "pass": False,
                            "notes": f"No motor connected (MO={mo_verify})"
                        })
                        summary[axis] = results
                        continue
                else:
                    print(f"Axis {axis}: Cannot verify servo status")
                    results.append({
                        "axis": axis,
                        "test_type": "motor_detection", 
                        "pass": False,
                        "notes": f"Cannot verify servo status"
                    })
                    summary[axis] = results
                    continue
        except Exception as e:
            print(f"Axis {axis}: Cannot check motor status: {e}")
            results.append({
                "axis": axis,
                "test_type": "motor_detection", 
                "pass": False,
                "notes": f"Cannot check motor status: {e}"
            })
            summary[axis] = results
            continue
        
        # Motor detected - run comprehensive tests
        print(f"Axis {axis}: Starting comprehensive movement tests")
        
        # Get starting position
        try:
            start_pos = _tp(g, axis)
            print(f"Axis {axis}: Starting position = {start_pos}")
        except Exception as e:
            print(f"Axis {axis}: Cannot read position: {e}")
            results.append({
                "axis": axis,
                "test_type": "position_read",
                "pass": False,
                "notes": f"Cannot read position: {e}"
            })
            summary[axis] = results
            continue
        
        # Test each speed in both directions
        for speed in test_speeds:
            print(f"Axis {axis}: Testing speed {speed} counts/sec")
            
            # Test positive direction
            try:
                print(f"Axis {axis}: Positive direction at {speed} counts/sec for {test_duration_seconds}s")
                _test_directional_movement(g, axis, speed, test_duration_seconds, movement_distance, "positive", results)
            except Exception as e:
                print(f"Axis {axis}: Positive direction test failed: {e}")
                results.append({
                    "axis": axis,
                    "test_type": f"positive_{speed}",
                    "pass": False,
                    "notes": f"Positive direction test failed: {e}"
                })
            
            # Test negative direction  
            try:
                print(f"Axis {axis}: Negative direction at {speed} counts/sec for {test_duration_seconds}s")
                _test_directional_movement(g, axis, -speed, test_duration_seconds, movement_distance, "negative", results)
            except Exception as e:
                print(f"Axis {axis}: Negative direction test failed: {e}")
                results.append({
                    "axis": axis,
                    "test_type": f"negative_{speed}",
                    "pass": False,
                    "notes": f"Negative direction test failed: {e}"
                })
        
        # Return to starting position
        try:
            print(f"Axis {axis}: Returning to starting position")
            _return_to_start_position(g, axis, start_pos)
        except Exception as e:
            print(f"Axis {axis}: Warning - could not return to start position: {e}")
        
        print(f"Axis {axis}: Testing complete")
        summary[axis] = results
    
    print("=== COMPREHENSIVE TESTING COMPLETE ===")
    return summary

def _test_directional_movement(g, axis: str, speed: int, duration_seconds: int, max_distance: int, direction: str, results: List[Dict]) -> None:
    """Test movement in one direction for specified duration"""
    try:
        # Set up motion parameters
        _cmd(g, f"SP{axis}={abs(speed)}")
        _cmd(g, f"AC{axis}={abs(speed) * 2}")  # 2x speed for acceleration
        _cmd(g, f"DC{axis}={abs(speed) * 2}")  # 2x speed for deceleration
        
        # Calculate target position (limit to max_distance)
        current_pos = _tp(g, axis)
        target_distance = min(abs(speed) * duration_seconds, max_distance)
        target_pos = current_pos + (target_distance if speed > 0 else -target_distance)
        
        print(f"Axis {axis}: Moving from {current_pos} to {target_pos} ({direction})")
        
        # Check servo status before movement
        try:
            mo_status = _cmd(g, f"MG _MO{axis}")
            if mo_status and mo_status != "?":
                mo_value = float(mo_status.split(",")[0])
                if mo_value != 0.0:
                    print(f"Axis {axis}: Servo not enabled before movement (MO={mo_value}), attempting to enable")
                    _cmd(g, f"SH{axis}")
                    # Check again
                    mo_check = _cmd(g, f"MG _MO{axis}")
                    if mo_check and mo_check != "?":
                        mo_verify = float(mo_check.split(",")[0])
                        if mo_verify != 0.0:
                            print(f"Axis {axis}: Failed to enable servo (MO={mo_verify})")
                            return
                        else:
                            print(f"Axis {axis}: Servo enabled successfully")
                    else:
                        print(f"Axis {axis}: Cannot verify servo status after enable")
                        return
                else:
                    print(f"Axis {axis}: Servo already enabled (MO={mo_value})")
            else:
                print(f"Axis {axis}: Cannot read servo status, attempting to enable")
                _cmd(g, f"SH{axis}")
                # Check again
                mo_check = _cmd(g, f"MG _MO{axis}")
                if mo_check and mo_check != "?":
                    mo_verify = float(mo_check.split(",")[0])
                    if mo_verify == 0.0:
                        print(f"Axis {axis}: Servo enabled successfully")
                    else:
                        print(f"Axis {axis}: Failed to enable servo (MO={mo_verify})")
                        return
                else:
                    print(f"Axis {axis}: Cannot verify servo status")
                    return
        except Exception as e:
            print(f"Axis {axis}: Error checking servo status: {e}")
            return
        
        # Execute movement
        _cmd(g, f"PA{axis}={int(target_pos)}")
        _cmd(g, f"BG{axis}")
        
        # Wait for specified duration or until motion completes
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                # Check if motion is still active
                bg_status = _cmd(g, f"MG _BG{axis}")
                if bg_status and bg_status != "?":
                    bg_value = float(bg_status.split(",")[0])
                    if bg_value == 0.0:  # Motion complete
                        print(f"Axis {axis}: Motion completed early at {time.time() - start_time:.1f}s")
                        break
            except:
                pass
            time.sleep(0.1)
        
        # Stop motion and wait for completion
        _cmd(g, f"ST{axis}")
        _wait_for_motion_complete(g, axis)
        
        # Check final position
        final_pos = _tp(g, axis)
        distance_moved = abs(final_pos - current_pos)
        expected_distance = min(abs(speed) * duration_seconds, max_distance)
        
        # Determine if test passed (moved at least 50% of expected distance)
        test_passed = distance_moved >= (expected_distance * 0.5)
        
        print(f"Axis {axis}: {direction} test - moved {distance_moved:.0f} counts (expected ~{expected_distance:.0f})")
        
        results.append({
            "axis": axis,
            "test_type": f"{direction}_{abs(speed)}",
            "speed": abs(speed),
            "duration": duration_seconds,
            "start_pos": current_pos,
            "final_pos": final_pos,
            "distance_moved": distance_moved,
            "expected_distance": expected_distance,
            "pass": test_passed,
            "notes": f"Moved {distance_moved:.0f} counts in {direction} direction"
        })
        
    except Exception as e:
        print(f"Axis {axis}: {direction} movement test error: {e}")
        results.append({
            "axis": axis,
            "test_type": f"{direction}_{abs(speed)}",
            "pass": False,
            "notes": f"Movement test error: {e}"
        })

def _return_to_start_position(g, axis: str, start_pos: float) -> None:
    """Return axis to starting position"""
    try:
        _cmd(g, f"SP{axis}=2000")  # Moderate speed for return
        _cmd(g, f"AC{axis}=4000")
        _cmd(g, f"DC{axis}=4000")
        _cmd(g, f"PA{axis}={int(start_pos)}")
        _cmd(g, f"BG{axis}")
        _wait_for_motion_complete(g, axis)
    except Exception as e:
        print(f"Warning: Could not return axis {axis} to start position: {e}")

def run_motion_tests(
    g,
    axes: AxisList,
    profiles: List[Dict[str, int]],
    target_offsets: List[int],
    tol_counts: int = 5,
    include_jog: bool = False,
    jog_speed: int = 5000,
    jog_dwell_ms: int = 500,
) -> Dict[str, List[Dict[str, Union[float, int, bool]]]]:
    """
    For each axis:
      - Check servo status first
      - Capture base = TPX
      - For each profile {sp,ac,dc}:
           SP/AC/DC
           For each offset in target_offsets:
               absolute_target = base + offset
               PA/BG/AM → verify ±tol_counts
           (optional) brief jog segment JGX/STX
    Uses only: SP, AC, DC, PA, BGX, TPX, @ABS, MG (optional JGX, STX)
    NOTE: AM/WT are program-only trippoints, use _BG polling instead
    """
    ax_list = _norm_axes(axes)
    summary: Dict[str, List[Dict[str, Union[float, int, bool]]]] = {}

    for axis in ax_list:
        results: List[Dict[str, Union[float, int, bool]]] = []

        # Check servo status first - skip if servo not enabled
        try:
            mo_status = _cmd(g, f"MG _MO{axis}")
            mo_value = float(mo_status.split(",")[0]) if mo_status else 1.0
            if mo_value != 0.0:
                # Servo not enabled, skip motion testing for this axis
                print(f"== AX {axis} SKIPPED - Servo not enabled (MO={mo_value})")
                results.append({
                    "axis": axis,
                    "target": 0,
                    "actual": 0,
                    "error": 0,
                    "pass": False,
                    "notes": f"Servo not enabled (MO={mo_value})"
                })
                summary[axis] = results
                continue
        except Exception as e:
            # If we can't check servo status, skip this axis
            print(f"== AX {axis} SKIPPED - Cannot check servo status: {e}")
            results.append({
                "axis": axis,
                "target": 0,
                "actual": 0,
                "error": 0,
                "pass": False,
                "notes": f"Cannot check servo status: {e}"
            })
            summary[axis] = results
            continue

        # Base position (no DP used in this section)
        base = _tp(g, axis)
        print(f"== AX {axis} START base={base}")

        for i, prof in enumerate(profiles, start=1):
            sp = int(prof.get("sp", 128000))
            ac = int(prof.get("ac", 2560000))
            dc = int(prof.get("dc", 2560000))

            # Announce profile
            print(f"AX {axis} PROFILE {i} SP={sp} AC={ac} DC={dc}")

            # Apply profile
            _set_profile(g, axis, sp=sp, ac=ac, dc=dc)

            # Run through targets (absolute positions based on current base)
            for off in target_offsets:
                target = int(round(base + off))
                res = _move_and_verify(g, axis, target, tol_counts)
                # Host-side, also log pass/fail quickly
                print(f"AX {axis} @ {target} {'PASS' if res['pass'] else 'FAIL'}")
                results.append(res)

            # Optional jog exercise between profiles
            if include_jog:
                optional_jog(g, axis, jg_speed=jog_speed, dwell_ms=jog_dwell_ms)

        # Finish axis
        print(f"== AX {axis} COMPLETE")
        summary[axis] = results

    return summary
