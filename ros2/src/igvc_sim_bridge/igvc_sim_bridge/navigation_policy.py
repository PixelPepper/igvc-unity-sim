"""Forward autonomy command policy; manual teleoperation remains separate."""
import math


def forward_command_allowed(linear, angular):
    """Reject reverse, pivot and sub-metre-radius turns without altering curvature.

    Replacing an unsafe command with a stop preserves collision-check semantics;
    clipping only angular velocity would turn a checked arc into a different path.
    This is a command guard, not proof of complete route topology.
    """
    if not math.isfinite(linear) or not math.isfinite(angular) or linear < 0:
        return False
    return abs(angular) <= max(linear, 1e-6)
