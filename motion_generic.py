# motion_generic.py
# Generic motion testing that works for both servo and stepper axes

def move_absolute_and_check(io, axis: str, target: int, sp=5000, ac=25000, dc=25000, tol=5):
    """
    Move to absolute position and check accuracy.
    Works for both servo and stepper axes.
    """
    # Set profile and move
    io.sp(axis, sp)
    io.ac(axis, ac) 
    io.dc(axis, dc)
    io.pa(axis, target)
    io.bg(axis)
    io.am(axis)
    
    # Check final position
    pos = io.tp(axis)
    err = abs(pos - target)
    return pos, err, (err <= tol)

def move_relative_and_check(io, axis: str, distance: int, sp=5000, ac=25000, dc=25000, tol=5):
    """
    Move relative distance and check accuracy.
    Works for both servo and stepper axes.
    """
    # Get initial position
    initial_pos = io.tp(axis)
    target = initial_pos + distance
    
    # Set profile and move
    io.sp(axis, sp)
    io.ac(axis, ac)
    io.dc(axis, dc)
    io.pr(axis, distance)  # Relative move
    io.bg(axis)
    io.am(axis)
    
    # Check final position
    pos = io.tp(axis)
    err = abs(pos - target)
    return pos, err, (err <= tol)
