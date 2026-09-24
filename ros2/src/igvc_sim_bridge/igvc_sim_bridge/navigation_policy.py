"""Forward autonomy command policy; manual teleoperation remains separate."""
import math


def forward_command_allowed(linear, angular):
    """Allow slow straight backup; reject pivots and tight forward turns.

    Replacing an unsafe command with a stop preserves collision-check semantics;
    clipping only angular velocity would turn a checked arc into a different path.
    This is a command guard, not proof of complete route topology.
    """
    if not math.isfinite(linear) or not math.isfinite(angular):
        return False
    if linear < 0:
        return linear >= -.100001 and abs(angular) <= 1e-6
    return abs(angular) <= max(2.0 * linear, 1e-6)
