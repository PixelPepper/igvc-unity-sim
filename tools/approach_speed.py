"""Waypoint braking cap; a positive floor avoids Nav2's zero/unlimited sentinel."""
import math


def approach_speed(distance: float, *, maximum: float = 2.2,
                   deceleration: float = 2.0, latency: float = 0.2,
                   reserve: float = 0.2) -> float:
    """Return an absolute SpeedLimit in m/s, bounded to [0.05, maximum].

    ``distance`` is remaining distance in metres. This cap budgets latency travel
    plus constant-deceleration braking before the arrival reserve. It does not
    implement the separate 2 m/s² acceleration ramp or issue a stop: inside the
    reserve, the caller must handle arrival/cancellation rather than use zero.
    """
    if not all(math.isfinite(v) for v in (distance, maximum, deceleration, latency, reserve)):
        raise ValueError('Approach-speed inputs must be finite')
    if distance < 0 or not 0.05 <= maximum <= 2.2:
        raise ValueError('Distance must be nonnegative and maximum must be 0.05 to 2.2 m/s')
    if deceleration <= 0 or latency < 0 or reserve < 0:
        raise ValueError('Deceleration must be positive; latency and reserve must be nonnegative')
    available = max(distance - reserve, 0.0)
    delay_velocity = deceleration * latency
    cap = math.sqrt(delay_velocity**2 + 2 * deceleration * available) - delay_velocity
    return max(0.05, min(maximum, cap))
