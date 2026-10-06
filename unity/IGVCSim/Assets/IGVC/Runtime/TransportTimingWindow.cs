using System;
using System.Globalization;
using System.Text;

namespace IGVC
{
    /// <summary>
    /// Pure, deterministic aggregation for the opt-in transport timing trace (no UnityEngine use).
    /// Frame samples arrive as monotonic seconds plus probe simulation time; at most one compact
    /// JSON record is produced per reporting interval, and the total number of records is capped.
    /// A frame gap is attributed to the window in which the late frame arrives, and the cumulative
    /// maximum is kept across windows, so a hitch is never lost at a reporting boundary.
    /// Coverage is one continuous interval: once stopped (component disabled/destroyed) or exhausted,
    /// nothing more is sampled, so a suspension is never measured as a frame gap.
    /// Schema v3 adds an independent FixedUpdate sample stream and connection-error flags read on every
    /// sampled Update and FixedUpdate. Fixed samples belong to the record emitted after them (not to the
    /// Update window start); a fixed gap is attributed to the record in which its later sample arrives, and
    /// the last fixed sample time is carried across records so a gap that spans a boundary stays visible.
    /// </summary>
    public sealed class TransportTimingWindow
    {
        public const string Schema = "igvc_transport_timing_v3";
        public const int DefaultRecordCap = 1200;
        public const string QueueFullPrefix = "Queue full! Messages are getting dropped!";

        private readonly double interval;
        private readonly int recordCap;
        private double lastFrame = double.NaN, windowStart = double.NaN;
        private double windowMaxGap, cumulativeMaxGap, simStart = double.NaN, simEnd = double.NaN;
        private long windowFrames, totalFrames, warningsTotal;
        private long windowUpdateErrors, totalUpdateErrors;
        // FixedUpdate stream: NaN means unavailable (no sample, or no gap yet), never zero.
        private double lastFixed = double.NaN, windowFixedFirst = double.NaN, fixedSimStart = double.NaN, fixedSimEnd = double.NaN;
        private double windowMaxFixedGap = double.NaN, windowMaxFixedGapEnd = double.NaN;
        private double cumulativeMaxFixedGap = double.NaN, cumulativeMaxFixedGapEnd = double.NaN;
        private long windowFixed, totalFixed, windowFixedErrors, totalFixedErrors;
        private int records;
        private bool stopped;

        public TransportTimingWindow(double reportIntervalSeconds = 1.0, int recordCap = DefaultRecordCap)
        {
            if (!(reportIntervalSeconds > 0) || double.IsInfinity(reportIntervalSeconds))
                throw new ArgumentOutOfRangeException(nameof(reportIntervalSeconds));
            if (recordCap < 2) throw new ArgumentOutOfRangeException(nameof(recordCap), "header plus final record");
            interval = reportIntervalSeconds;
            this.recordCap = recordCap;
        }

        public int Records => records;
        public bool Exhausted => records >= recordCap;
        /// <summary>True once coverage has ended (stopped or exhausted); no further samples or records.</summary>
        public bool Ended => stopped || Exhausted;
        public double CumulativeMaxFrameGap => cumulativeMaxGap;
        public long TotalFrames => totalFrames;
        public long TotalFixedSamples => totalFixed;
        /// <summary>NaN until two fixed samples have been observed.</summary>
        public double CumulativeMaxFixedGap => cumulativeMaxFixedGap;

        /// <summary>The single header record describing clocks, coverage and semantics; counts as one record.</summary>
        public string Header(string utcIso, double monoBeforeUtc, double monoAfterUtc, string clockSource,
                             long frequencyHz, long originTicks)
        {
            if (records != 0) throw new InvalidOperationException("header already written");
            records++;
            var b = new StringBuilder(3200);
            b.Append("{\"schema\":\"").Append(Schema).Append("\",\"kind\":\"header\",\"seq\":0");
            Utc(b, utcIso, monoBeforeUtc, monoAfterUtc);
            Field(b, "mono_source", clockSource);
            b.Append(",\"mono_frequency_hz\":").Append(frequencyHz.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"mono_origin_ticks\":").Append(originTicks.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"report_interval_s\":").Append(Num(interval));
            b.Append(",\"record_cap\":").Append(recordCap.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"nominal_exhaustion_after_first_sample_s\":").Append(Num((recordCap - 1) * interval));
            Field(b, "queue_full_prefix", QueueFullPrefix);
            Field(b, "clock_semantics", "mono_s = (ticks - origin) / frequency on this host. Each utc is read between mono_before_utc_s and mono_after_utc_s; that bracket bounds the read's placement, not utc accuracy. DateTime.UtcNow can be coarse (milliseconds) and can step (time sync or manual change). No synchronization with ROS, WSL or other hosts' clocks is implied. Numbers are raw double encodings; digits beyond each clock's resolution are not accuracy.");
            Field(b, "coverage_semantics", "One continuous interval from this header until a final record (kind stopped or exhausted). Disable or destroy ends tracing permanently; there is no resume, and nothing (frames or warnings) is observed after the final record. Records stop at record_cap. nominal_exhaustion_after_first_sample_s assumes uninterrupted frames after the first sample; delays lengthen coverage, so it is not a maximum. Use actual header/final clocks and account for unsampled tails; a later event is not covered.");
            Field(b, "warning_semantics", "Counts are connector log lines starting with queue_full_prefix, as observed by the log callback; they are not counts of dropped messages and carry no drop or wire time. Zero means no matching line was observed, not proof that nothing was dropped (the text could change; nothing is observed outside coverage). Count and last-observation time are updated separately and asynchronously, so a window's count and the cumulative last-observation time are not an atomic pair and are not exact window attribution.");
            Field(b, "queue_depth", "unavailable: actual connector backlog is not public; QueueSize is capacity and LastMessageSentRealtime marks enqueue, not socket delivery");
            Field(b, "frame_semantics", "frame gap = wall time between consecutive Update samples while covered, not a transport diagnosis; focus loss, pause, GC, OS suspension or rendering stalls may contribute. mono_s is the last sampled frame, not emission or stop time; a final unsampled tail is not measured as a frame gap; attributed to the window in which the late frame arrives. A record is emitted only on a frame, so a hitch is reported after it ends; sim time is TransportProbe.SimTime read in this component's Update, whose order relative to TransportProbe.Update is unspecified (may lag one frame).");
            Field(b, "sample_stream_semantics", "Two independent sample streams. Update stream: frames, frame gaps and update_error_samples (Update samples whose ROSConnection.HasConnectionError read was true), window starting at the previous record's last frame. FixedUpdate stream: fixed_* fields count FixedUpdate samples observed since the previous record was built (not since window_start_mono_s); a fixed gap is attributed to the record in which its later sample arrives, with its end time, and cumulative_last_fixed_mono_s carries the last fixed sample across records so a gap spanning a boundary stays visible. connection_error is a separate read at record time. Error flags are asynchronous bool reads: counts are of samples, not exact intervals or durations, and zero does not prove no error occurred. A fixed gap means no sampled FixedUpdate callback in that period, not a unique main-thread cause. Fixed sim time is TransportProbe.SimTime read in FixedUpdate with unspecified component order; it proves neither publish, enqueue, send nor delivery, nor alignment with other hosts. Zero fixed samples means fixed timing is unavailable, not healthy.");
            return b.Append('}').ToString();
        }

        /// <summary>Record one frame. Returns true when a periodic record is due (caller then calls Emit).</summary>
        public bool Sample(double monotonicSeconds, double simTime, bool connectionError)
        {
            if (Ended || double.IsNaN(monotonicSeconds) || double.IsInfinity(monotonicSeconds)) return false;
            if (connectionError) { windowUpdateErrors++; totalUpdateErrors++; }
            if (!double.IsNaN(lastFrame))
            {
                double gap = monotonicSeconds - lastFrame;
                if (gap > windowMaxGap) windowMaxGap = gap;
                if (gap > cumulativeMaxGap) cumulativeMaxGap = gap;
            }
            if (double.IsNaN(windowStart)) windowStart = monotonicSeconds;
            if (double.IsNaN(simStart)) simStart = simTime;
            simEnd = simTime;
            lastFrame = monotonicSeconds;
            windowFrames++;
            totalFrames++;
            return monotonicSeconds - windowStart >= interval;
        }

        /// <summary>Record one FixedUpdate observation (independent stream; never makes a record due).</summary>
        public void SampleFixed(double monotonicSeconds, double simTime, bool connectionError)
        {
            if (Ended || double.IsNaN(monotonicSeconds) || double.IsInfinity(monotonicSeconds)) return;
            if (!double.IsNaN(lastFixed))
            {
                double gap = monotonicSeconds - lastFixed;
                if (double.IsNaN(windowMaxFixedGap) || gap > windowMaxFixedGap) { windowMaxFixedGap = gap; windowMaxFixedGapEnd = monotonicSeconds; }
                if (double.IsNaN(cumulativeMaxFixedGap) || gap > cumulativeMaxFixedGap) { cumulativeMaxFixedGap = gap; cumulativeMaxFixedGapEnd = monotonicSeconds; }
            }
            if (windowFixed == 0) { windowFixedFirst = monotonicSeconds; fixedSimStart = simTime; }
            fixedSimEnd = simTime;
            lastFixed = monotonicSeconds;
            windowFixed++;
            totalFixed++;
            if (connectionError) { windowFixedErrors++; totalFixedErrors++; }
        }

        /// <summary>
        /// Build the due periodic record and start the next window. The last record allowed by the cap
        /// is an explicit exhaustion record, after which no more are produced.
        /// </summary>
        public string Emit(string utcIso, double monoBeforeUtc, double monoAfterUtc, long queueFullDelta,
                           double lastQueueFullMonotonic, bool connectionError)
        {
            if (Ended) return null;
            string record = Record(Exhausting ? "exhausted" : "window", utcIso, monoBeforeUtc, monoAfterUtc,
                                   queueFullDelta, lastQueueFullMonotonic, connectionError,
                                   Exhausting ? "record cap reached; tracing stopped" : null);
            windowStart = lastFrame;
            windowFrames = 0;
            windowMaxGap = 0;
            simStart = simEnd;
            windowUpdateErrors = 0;
            windowFixed = windowFixedErrors = 0;
            windowFixedFirst = windowMaxFixedGap = windowMaxFixedGapEnd = fixedSimStart = fixedSimEnd = double.NaN;
            return record;
        }

        /// <summary>
        /// End coverage permanently (for example on disable/destroy) with one labelled final record covering the
        /// partial window. Returns null if coverage had already ended.
        /// </summary>
        public string Stop(string reason, string utcIso, double monoBeforeUtc, double monoAfterUtc, long queueFullDelta,
                           double lastQueueFullMonotonic, bool connectionError)
        {
            if (Ended) return null;
            string record = Record("stopped", utcIso, monoBeforeUtc, monoAfterUtc, queueFullDelta,
                                   lastQueueFullMonotonic, connectionError, "coverage ended: " + reason);
            stopped = true;
            return record;
        }

        private bool Exhausting => records == recordCap - 1;

        private string Record(string kind, string utcIso, double monoBeforeUtc, double monoAfterUtc, long queueFullDelta,
                              double lastQueueFullMonotonic, bool connectionError, string note)
        {
            long delta = Math.Max(0, queueFullDelta);
            warningsTotal += delta;
            var b = new StringBuilder(1024);
            b.Append("{\"schema\":\"").Append(Schema).Append("\",\"kind\":\"").Append(kind).Append('"');
            b.Append(",\"seq\":").Append(records.ToString(CultureInfo.InvariantCulture));
            Utc(b, utcIso, monoBeforeUtc, monoAfterUtc);
            b.Append(",\"mono_s\":").Append(Num(lastFrame));
            b.Append(",\"window_start_mono_s\":").Append(Num(windowStart));
            b.Append(",\"frames\":").Append(windowFrames.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"total_frames\":").Append(totalFrames.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"window_max_frame_gap_s\":").Append(Num(windowMaxGap));
            b.Append(",\"cumulative_max_frame_gap_s\":").Append(Num(cumulativeMaxGap));
            b.Append(",\"sim_time_start_s\":").Append(Num(simStart));
            b.Append(",\"sim_time_end_s\":").Append(Num(simEnd));
            b.Append(",\"queue_full_lines_since_previous_record\":").Append(delta.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"queue_full_lines_total\":").Append(warningsTotal.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"cumulative_last_queue_full_observed_mono_s\":")
             .Append(double.IsNaN(lastQueueFullMonotonic) ? "null" : Num(lastQueueFullMonotonic));
            b.Append(",\"connection_error\":").Append(connectionError ? "true" : "false");
            b.Append(",\"update_error_samples\":").Append(windowUpdateErrors.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"total_update_error_samples\":").Append(totalUpdateErrors.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"fixed_samples\":").Append(windowFixed.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"total_fixed_samples\":").Append(totalFixed.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"fixed_error_samples\":").Append(windowFixedErrors.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"total_fixed_error_samples\":").Append(totalFixedErrors.ToString(CultureInfo.InvariantCulture));
            b.Append(",\"fixed_first_mono_s\":").Append(windowFixed > 0 ? Num(windowFixedFirst) : "null");
            b.Append(",\"fixed_last_mono_s\":").Append(windowFixed > 0 ? Num(lastFixed) : "null");
            b.Append(",\"cumulative_last_fixed_mono_s\":").Append(Num(lastFixed));
            b.Append(",\"window_max_fixed_gap_s\":").Append(Num(windowMaxFixedGap));
            b.Append(",\"window_max_fixed_gap_end_mono_s\":").Append(Num(windowMaxFixedGapEnd));
            b.Append(",\"cumulative_max_fixed_gap_s\":").Append(Num(cumulativeMaxFixedGap));
            b.Append(",\"cumulative_max_fixed_gap_end_mono_s\":").Append(Num(cumulativeMaxFixedGapEnd));
            b.Append(",\"fixed_sim_time_start_s\":").Append(windowFixed > 0 ? Num(fixedSimStart) : "null");
            b.Append(",\"fixed_sim_time_end_s\":").Append(windowFixed > 0 ? Num(fixedSimEnd) : "null");
            if (note != null) Field(b, "note", note);
            records++;
            return b.Append('}').ToString();
        }

        private static void Utc(StringBuilder b, string utcIso, double before, double after)
        {
            Field(b, "utc", utcIso);
            b.Append(",\"mono_before_utc_s\":").Append(Num(before));
            b.Append(",\"mono_after_utc_s\":").Append(Num(after));
        }

        private static string Num(double value) =>
            double.IsNaN(value) || double.IsInfinity(value) ? "null" : value.ToString("R", CultureInfo.InvariantCulture);

        private static void Field(StringBuilder b, string key, string value)
        {
            b.Append(",\"").Append(key).Append("\":\"");
            foreach (char c in value ?? "")
            {
                if (c == '"' || c == '\\') b.Append('\\').Append(c);
                else if (c < ' ') b.Append(' ');
                else b.Append(c);
            }
            b.Append('"');
        }
    }
}
