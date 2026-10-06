using System;
using System.Diagnostics;
using System.Globalization;
using System.Threading;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace IGVC
{
    /// <summary>
    /// OPT-IN, observe-only timing trace. Added only by an explicit opt-in hookup, then Initialize()d once.
    /// Each Update samples a Stopwatch monotonic clock, the frame gap, the probe SimTime and the connection-error
    /// flag into a TransportTimingWindow; each FixedUpdate samples the same into an independent fixed stream.
    /// At most one compact JSON Debug.Log record per wall second, capped in total.
    /// The threaded log callback only counts the connector's exact queue-full warning with Interlocked
    /// operations (no Unity API, no allocation, no logging); counts are folded into the next record.
    /// Coverage is one continuous interval: disabling or destroying the component ends tracing permanently
    /// with a labelled final record (no resume), so a suspension is never reported as a frame gap.
    /// It never changes motion, publishers, physics, ROS topics or the connection.
    /// </summary>
    public sealed class TransportTimingTrace : MonoBehaviour
    {
        private TransportProbe probe;
        private ROSConnection ros;
        private TransportTimingWindow window;
        private long originTicks;
        private bool initialized, subscribed;
        private long queueFullCount, queueFullTakenCount;
        private long lastQueueFullTicks = long.MinValue;

        /// <summary>Idempotent: a second call is ignored. Both references are required and cached.</summary>
        public void Initialize(TransportProbe sourceProbe, ROSConnection connection, double reportIntervalSeconds = 1.0,
                               int recordCap = TransportTimingWindow.DefaultRecordCap)
        {
            if (initialized) return;
            if (sourceProbe == null || connection == null) throw new ArgumentNullException(sourceProbe == null ? nameof(sourceProbe) : nameof(connection));
            probe = sourceProbe;
            ros = connection;
            window = new TransportTimingWindow(reportIntervalSeconds, recordCap);
            originTicks = Stopwatch.GetTimestamp();
            initialized = true;
            ReadUtc(out string utc, out double before, out double after);
            Debug.Log(window.Header(utc, before, after, "System.Diagnostics.Stopwatch", Stopwatch.Frequency, originTicks));
            if (isActiveAndEnabled) Subscribe();
            else End("not enabled at initialization");
        }

        private void OnDisable() => End("component disabled");
        private void OnDestroy() => End("component destroyed");

        private void Subscribe()
        {
            if (subscribed) return;
            Application.logMessageReceivedThreaded += OnLog;
            subscribed = true;
        }

        private void Unsubscribe()
        {
            if (!subscribed) return;
            Application.logMessageReceivedThreaded -= OnLog;
            subscribed = false;
        }

        // Any thread. Only bounded, lock-free counter updates; Stopwatch is pure .NET.
        private void OnLog(string condition, string stackTrace, LogType type)
        {
            if (type != LogType.Warning || condition == null
                || !condition.StartsWith(TransportTimingWindow.QueueFullPrefix, StringComparison.Ordinal)) return;
            Interlocked.Increment(ref queueFullCount);
            Interlocked.Exchange(ref lastQueueFullTicks, Stopwatch.GetTimestamp());
        }

        private double Mono(long ticks) => (ticks - originTicks) / (double)Stopwatch.Frequency;

        // The UTC read is bracketed by monotonic reads so its placement on the monotonic clock is bounded.
        private void ReadUtc(out string utc, out double before, out double after)
        {
            long a = Stopwatch.GetTimestamp();
            utc = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture);
            long b = Stopwatch.GetTimestamp();
            before = Mono(a);
            after = Mono(b);
        }

        private long TakeWarnings(out double lastObserved)
        {
            long total = Interlocked.Read(ref queueFullCount);
            long delta = total - queueFullTakenCount;
            queueFullTakenCount = total;
            long lastTicks = Interlocked.Read(ref lastQueueFullTicks);
            lastObserved = lastTicks == long.MinValue ? double.NaN : Mono(lastTicks);
            return delta;
        }

        /// <summary>End coverage permanently: unsubscribe first, then log one final record if any was still due.</summary>
        private void End(string reason)
        {
            Unsubscribe();
            if (!initialized || window.Ended) return;
            long delta = TakeWarnings(out double lastObserved);
            ReadUtc(out string utc, out double before, out double after);
            string record = window.Stop(reason, utc, before, after, delta, lastObserved, ros != null && ros.HasConnectionError);
            if (record != null) Debug.Log(record);
        }

        // Observation only: one clock read, SimTime and the connection-error bool per physics step; never makes a record due.
        private void FixedUpdate()
        {
            if (!initialized || window.Ended) return;
            window.SampleFixed(Mono(Stopwatch.GetTimestamp()), probe.SimTime, ros.HasConnectionError);
        }

        private void Update()
        {
            if (!initialized || window.Ended) return;
            if (!window.Sample(Mono(Stopwatch.GetTimestamp()), probe.SimTime, ros.HasConnectionError)) return;
            long delta = TakeWarnings(out double lastObserved);
            ReadUtc(out string utc, out double before, out double after);
            string record = window.Emit(utc, before, after, delta, lastObserved, ros.HasConnectionError);
            if (record != null) Debug.Log(record);
            if (window.Ended)
            {
                Unsubscribe();
                enabled = false;  // OnDisable then finds coverage already ended and logs nothing more
            }
        }
    }
}
