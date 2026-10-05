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
    /// </summary>
    public sealed class TransportTimingWindow
    {
        public const string Schema = "igvc_transport_timing_v2";
        public const int DefaultRecordCap = 1200;
        public const string QueueFullPrefix = "Queue full! Messages are getting dropped!";

        private readonly double interval;
        private readonly int recordCap;
        private double lastFrame = double.NaN, windowStart = double.NaN;
        private double windowMaxGap, cumulativeMaxGap, simStart = double.NaN, simEnd = double.NaN;
        private long windowFrames, totalFrames, warningsTotal;
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

        /// <summary>The single header record describing clocks, coverage and semantics; counts as one record.</summary>
        public string Header(string utcIso, double monoBeforeUtc, double monoAfterUtc, string clockSource,
                             long frequencyHz, long originTicks)
        {
            if (records != 0) throw new InvalidOperationException("header already written");
            records++;
            var b = new StringBuilder(1400);
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
            return b.Append('}').ToString();
        }

        /// <summary>Record one frame. Returns true when a periodic record is due (caller then calls Emit).</summary>
        public bool Sample(double monotonicSeconds, double simTime)
        {
            if (Ended || double.IsNaN(monotonicSeconds) || double.IsInfinity(monotonicSeconds)) return false;
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
            var b = new StringBuilder(512);
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
