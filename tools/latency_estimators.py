"""Explicitly selected, clock-bound planning-latency estimators behind one interface (offline, unused yet).

Each admission attempt is described by one immutable AdmissionSample holding BOTH clocks; an
estimator reads only its own clock and never converts or retimes one into the other:

  odometry_header_interval_ema       interval = (admission_stamp_ns - planning_stamp_ns) * 1e-9 s
                                     (odometry header stamps of the planning and admission samples);
                                     exponential moving average, the first accepted sample replaces
                                     initial_latency_s. Defaults: initial 0.6 s, alpha 0.3.
  wall_submit_admission_lower_quartile
                                     interval = admission_wall_s - submit_wall_s (local monotonic);
                                     the lower order statistic sorted(window)[(n-1)//4] of the last
                                     ``window`` accepted samples. Defaults: initial 0.3 s, window 20.

Both share one gated sample policy (SAMPLE_POLICY, version SAMPLE_POLICY_VERSION; COMMON_REJECTS),
applied before any estimator value changes: missing, non-integer (bool excluded), equal or backward
odometry stamps, non-finite admission/receipt clocks, a receipt age that is not representable as a
finite float, negative, or above max_sample_age_s. Each estimator then rejects problems of its OWN
interval only (its ``rejects``): the EMA an odometry interval not representable as a finite float;
the wall estimator a missing or non-finite submit clock, a non-finite (e.g. overflowing) or negative
wall duration (zero is accepted); the EMA never reads the submit clock. Every rejection is counted
by reason and happens before clamping. Finite accepted intervals above max_latency_s are clamped to
it and counted. Rejections never change the estimate. "Finite" always includes Python ints too large
for a float: they are rejected (or raise ValueError in constructors), never an OverflowError.

The lower-quartile ARITHMETIC matches the legacy latency_compensation estimator, but this is not the
legacy end-to-end experiment: the legacy code admitted any finite wall interval without this gate
and pairs with different prediction bounds. This module holds no predictor, pose, course or grid
input and makes no claim about which estimator is better or safer.
"""
from collections import deque
from dataclasses import dataclass
import math
from typing import Optional

EMA = 'odometry_header_interval_ema'
LOWER_QUARTILE = 'wall_submit_admission_lower_quartile'
KINDS = (EMA, LOWER_QUARTILE)
ESTIMATOR_VERSION = 1
SAMPLE_POLICY = 'gated_admission_sample'
SAMPLE_POLICY_VERSION = 1
MAX_WINDOW = 1000

# Rejection reasons of the shared gate (every estimator), in check order.
COMMON_REJECTS = ('missing_odometry_stamp', 'invalid_odometry_stamp', 'no_new_odometry', 'odometry_clock_reset',
                  'invalid_receipt_clock', 'invalid_receipt_age', 'future_admission_receipt',
                  'stale_admission_sample')
# Each estimator's own interval checks (after the shared gate).
EMA_REJECTS = ('invalid_odometry_interval',)
LOWER_QUARTILE_REJECTS = ('missing_submit_clock', 'invalid_submit_clock', 'invalid_wall_interval',
                          'negative_wall_interval')


@dataclass(frozen=True)
class AdmissionSample:
    """One admission attempt. Units: stamps in integer nanoseconds of the odometry header clock;
    *_wall_s in seconds of the local monotonic clock (time.monotonic()).

    planning_stamp_ns          header stamp of the odometry message the plan started from
    admission_stamp_ns         header stamp of the odometry message used at admission
    submit_wall_s              local monotonic time the plan was submitted (wall estimator only)
    admission_wall_s           local monotonic time of the admission attempt ("now")
    admission_receipt_wall_s   local monotonic receipt time of the admission odometry message
    """
    planning_stamp_ns: Optional[int]
    admission_stamp_ns: Optional[int]
    submit_wall_s: Optional[float]
    admission_wall_s: Optional[float]
    admission_receipt_wall_s: Optional[float]


@dataclass(frozen=True)
class Observation:
    """Result of observe_admission: accepted with the (possibly clamped) interval used, or a reason."""
    accepted: bool
    interval_s: Optional[float] = None
    clamped: bool = False
    reason: Optional[str] = None


@dataclass(frozen=True)
class EstimatorConfig:
    """Constructor settings, frozen for the estimator's lifetime (rules never change midway)."""
    initial_latency_s: float
    max_latency_s: float
    max_sample_age_s: float
    alpha: Optional[float] = None
    window: Optional[int] = None


def _real(value):
    """A finite int or float representable as a float, never a bool; never raises OverflowError."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # an int too large for a float
        return False


def _validate(initial_latency_s, max_latency_s, max_sample_age_s):
    for name, value in (('initial_latency_s', initial_latency_s), ('max_latency_s', max_latency_s),
                        ('max_sample_age_s', max_sample_age_s)):
        if not _real(value):
            raise ValueError(f'{name} must be a finite number (not bool), got {value!r}')
    if not 0 < max_latency_s <= 5:
        raise ValueError('max_latency_s must be in (0, 5]')
    if not 0 <= initial_latency_s <= max_latency_s:
        raise ValueError('initial_latency_s must be in [0, max_latency_s]')
    if not 0 < max_sample_age_s <= 1:
        raise ValueError('max_sample_age_s must be in (0, 1]')


class _GatedEstimator:
    kind = None
    timebase = None
    rejects = ()  # this estimator's own interval rejection reasons

    def __init__(self, config):
        self._config = config
        self._latency = float(config.initial_latency_s)
        self.samples = 0          # accepted samples (clamped ones included)
        self.clamped_samples = 0  # accepted samples clamped to max_latency_s
        self.rejected_samples = 0
        self.rejected = {}        # reason -> count

    @property
    def config(self):
        """The frozen EstimatorConfig; read-only (assigning ``config`` raises AttributeError)."""
        return self._config

    @property
    def latency(self):
        """Current estimate in seconds (initial_latency_s until the first accepted sample)."""
        return self._latency

    def _reject(self, reason):
        self.rejected_samples += 1
        self.rejected[reason] = self.rejected.get(reason, 0)+1
        return Observation(False, reason=reason)

    def _gate(self, sample):
        """Shared sample policy; returns a rejection reason or None."""
        a, b = sample.planning_stamp_ns, sample.admission_stamp_ns
        if a is None or b is None:
            return 'missing_odometry_stamp'
        if type(a) is not int or type(b) is not int:
            return 'invalid_odometry_stamp'
        if b == a:
            return 'no_new_odometry'
        if b < a:
            return 'odometry_clock_reset'
        if not (_real(sample.admission_wall_s) and _real(sample.admission_receipt_wall_s)):
            return 'invalid_receipt_clock'
        age = sample.admission_wall_s-sample.admission_receipt_wall_s
        if not _real(age):  # finite clocks whose difference overflows a float
            return 'invalid_receipt_age'
        if age < 0:
            return 'future_admission_receipt'
        if age > self.config.max_sample_age_s:
            return 'stale_admission_sample'
        return None

    def _interval(self, sample):
        """(interval seconds, None) from this estimator's own clock, or (None, rejection reason)."""
        raise NotImplementedError

    def _update(self, seconds):
        raise NotImplementedError

    def observe_admission(self, sample):
        """Gate one AdmissionSample; on acceptance update the estimate. Returns an Observation."""
        if not isinstance(sample, AdmissionSample):
            raise TypeError('observe_admission needs an AdmissionSample')
        reason = self._gate(sample)
        if reason is None:
            seconds, reason = self._interval(sample)
        if reason is not None:
            return self._reject(reason)
        clamped = seconds > self.config.max_latency_s
        if clamped:
            seconds = float(self.config.max_latency_s)
            self.clamped_samples += 1
        self._update(seconds)
        self.samples += 1
        return Observation(True, interval_s=seconds, clamped=clamped)

    def _rules(self):
        raise NotImplementedError

    def identity(self):
        """Fresh JSON-safe identity: algorithm, clock, sample policy and frozen configuration."""
        config = {k: v for k, v in vars(self.config).items() if v is not None}
        return dict(kind=self.kind, version=ESTIMATOR_VERSION, timebase=self.timebase, **self._rules(),
                    above_max_latency='clamp_and_count',
                    sample_policy=dict(id=SAMPLE_POLICY, version=SAMPLE_POLICY_VERSION, rejects=list(COMMON_REJECTS),
                                       receipt_age='admission_wall_s - admission_receipt_wall_s in '
                                                   '[0, max_sample_age_s]'),
                    rejects=list(self.rejects),
                    config=config)

    def report(self):
        """Fresh JSON-safe running state plus identity; callers may mutate it freely."""
        return dict(identity=self.identity(), latency_s=self._latency, samples=self.samples,
                    clamped_samples=self.clamped_samples, rejected_samples=self.rejected_samples,
                    rejected=dict(self.rejected))


class OdometryIntervalEMA(_GatedEstimator):
    kind = EMA
    timebase = 'odometry_header_stamp_ns'
    rejects = EMA_REJECTS

    def __init__(self, initial_latency_s=.6, alpha=.3, max_latency_s=1.2, max_sample_age_s=.25):
        _validate(initial_latency_s, max_latency_s, max_sample_age_s)
        if not _real(alpha) or not 0 < alpha <= 1:
            raise ValueError(f'alpha must be a number in (0, 1] (not bool), got {alpha!r}')
        super().__init__(EstimatorConfig(float(initial_latency_s), float(max_latency_s), float(max_sample_age_s),
                                         alpha=float(alpha)))

    def _interval(self, sample):
        # submit_wall_s is never read. The int delta is exact; its float conversion can overflow.
        try:
            seconds = (sample.admission_stamp_ns-sample.planning_stamp_ns)*1e-9
        except OverflowError:
            return None, 'invalid_odometry_interval'
        return (seconds, None) if math.isfinite(seconds) else (None, 'invalid_odometry_interval')

    def _update(self, seconds):
        a = self.config.alpha
        self._latency = seconds if self.samples == 0 else (1-a)*self._latency+a*seconds

    def _rules(self):
        return dict(interval='admission_stamp_ns - planning_stamp_ns', statistic='exponential_moving_average',
                    first_sample='replaces_initial', update='latency = (1-alpha)*latency + alpha*sample')


class WallSubmitAdmissionLowerQuartile(_GatedEstimator):
    kind = LOWER_QUARTILE
    timebase = 'local_monotonic_s'
    rejects = LOWER_QUARTILE_REJECTS

    def __init__(self, initial_latency_s=.3, window=20, max_latency_s=1.2, max_sample_age_s=.25):
        _validate(initial_latency_s, max_latency_s, max_sample_age_s)
        if type(window) is not int or not 1 <= window <= MAX_WINDOW:
            raise ValueError(f'window must be an int in [1, {MAX_WINDOW}] (not bool), got {window!r}')
        super().__init__(EstimatorConfig(float(initial_latency_s), float(max_latency_s), float(max_sample_age_s),
                                         window=window))
        self._window = deque(maxlen=window)

    def _interval(self, sample):
        if sample.submit_wall_s is None:
            return None, 'missing_submit_clock'
        if not _real(sample.submit_wall_s):
            return None, 'invalid_submit_clock'
        seconds = sample.admission_wall_s-sample.submit_wall_s
        if not _real(seconds):  # e.g. 1e308 - -1e308 overflows to inf: rejected, never clamped
            return None, 'invalid_wall_interval'
        if seconds < 0:
            return None, 'negative_wall_interval'
        return float(seconds), None

    def _update(self, seconds):
        self._window.append(seconds)
        ordered = sorted(self._window)
        self._latency = ordered[(len(ordered)-1)//4]

    def _rules(self):
        return dict(interval='admission_wall_s - submit_wall_s', statistic='sorted_window[(n-1)//4]',
                    first_sample='replaces_initial', window_contents='last accepted clamped samples',
                    legacy_relation='same lower-quartile arithmetic as latency_compensation v1; gated sample '
                                    'policy differs, so not the legacy end-to-end experiment')

    def report(self):
        result = super().report()
        result['window_samples'] = list(self._window)
        return result


_CONSTRUCTORS = {EMA: OdometryIntervalEMA, LOWER_QUARTILE: WallSubmitAdmissionLowerQuartile}


def make_estimator(kind, **config):
    """The estimator named exactly by ``kind`` (one of KINDS); no default and no fallback.

    Unknown kinds raise ValueError; settings the kind does not take raise TypeError.
    """
    if type(kind) is not str or kind not in _CONSTRUCTORS:
        raise ValueError(f'unknown latency estimator {kind!r}; choose one of {KINDS}')
    return _CONSTRUCTORS[kind](**config)
