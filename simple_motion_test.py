"""
Simple 4-Move Test for DMC-4143
Clean, repeatable sequence for axes A and B
"""

import time
from galil_helpers import (
    read_scalar, is_servo_on, ensure_servo_on,
    wait_motion_complete, set_motion_profile, zero_position,
    move_absolute, read_position
)

def simple_motion_test(g, axis="A", sp=80000, ac=400000, dc=400000):
    """
    Simple 4-move test sequence:
    1. Zero position counter
    2. Move to +50,000
    3. Return to 0
    4. Move to -50,000
    5. Return to 0
    
    Args:
        g: gclib controller handle
        axis: Axis to test ("A" or "B")
        sp: Speed (counts/s)
        ac: Acceleration (counts/s^2)
        dc: Deceleration (counts/s^2)
    """
    
    print(f"\n{'='*60}")
    print(f"SIMPLE MOTION TEST - AXIS {axis}")
    print(f"{'='*60}")
    
    # All helper functions imported from galil_helpers module
    
    # Step 1: Make sure axis is safe & enabled
    print(f"\n[1] Ensuring axis {axis} is safe and enabled...")
    ensure_servo_on(g, axis)
    print(f"    ✓ Servo enabled (MO=0)")
    
    # Step 2: Set motion profile
    print(f"\n[2] Setting motion profile...")
    set_motion_profile(g, axis, sp, ac, dc)
    print(f"    ✓ Motion profile set (SP={sp}, AC={ac}, DC={dc})")
    
    # Step 3: Zero the position counter
    print(f"\n[3] Zeroing position counter...")
    zero_position(g, axis)
    pos = read_position(g, axis)
    print(f"    ✓ Position zeroed: TP{axis} = {pos}")
    
    # Step 4: Run the 4-move sequence
    print(f"\n[4] Running 4-move sequence...")
    
    moves = [
        (50000, "Move to +50,000"),
        (0, "Return to 0"),
        (-50000, "Move to -50,000"),
        (0, "Final return to 0")
    ]
    
    for target, description in moves:
        print(f"\n    {description}:")
        move_absolute(g, axis, target, wait=True)
        
        pos = read_position(g, axis)
        error = abs(pos - target)
        print(f"        ✓ Motion complete: TP{axis} = {pos} (target={target}, error={error})")
        
        if error > 10:
            print(f"        ⚠ Warning: Position error {error} counts")
    
    # Step 5: Verify final position
    print(f"\n[5] Final verification...")
    final_pos = read_position(g, axis)
    print(f"    Final position: TP{axis} = {final_pos}")
    
    if abs(final_pos) < 10:
        print(f"\n{'='*60}")
        print(f"✅ TEST PASSED - Axis {axis} completed all 4 moves")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"\n{'='*60}")
        print(f"❌ TEST FAILED - Final position error: {final_pos} counts")
        print(f"{'='*60}\n")
        return False


if __name__ == "__main__":
    """Example usage"""
    import gclib
    
    # Connect to controller
    g = gclib.py()
    g.GOpen("10.1.0.21 -s ALL")
    
    try:
        # Test axis A
        simple_motion_test(g, axis="A", sp=80000, ac=400000, dc=400000)
        
        # Test axis B
        simple_motion_test(g, axis="B", sp=80000, ac=400000, dc=400000)
        
    finally:
        g.GClose()

