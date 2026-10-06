using System;
using System.Globalization;
using IGVC;
using UnityEngine;

/// <summary>Deterministic checks of the opt-in transport timing aggregation (pure TransportTimingWindow).</summary>
public static class TransportTimingChecks
{
    public static void Run() => RunCore(message => Debug.Log(message));

    /// <summary>Pure core; returns the number of passed checks and throws on the first failure.</summary>
    public static int RunCore(Action<string> pass)
    {
        int count = 0;
        void Check(bool value, string name)
        {
            if (!value) throw new Exception("FAIL " + name);
            count++;
            pass("PASS " + name);
        }
        bool Has(string record, string fragment) => record != null && record.Contains(fragment);
        string R(double value) => value.ToString("R", CultureInfo.InvariantCulture);
        const string Utc = "2026-10-05T00:00:00.0000000Z";
        TransportTimingWindow Fresh(int cap = 100)
        {
            var created = new TransportTimingWindow(1.0, cap);
            created.Header(Utc, 0, 0, "Stopwatch", 1, 0);
            return created;
        }
        string Emit(TransportTimingWindow target, long delta = 0, double last = double.NaN, bool error = false) =>
            target.Emit(Utc, 5, 5.001, delta, last, error);

        // Header: clock bracket, coverage, exact warning prefix and semantics.
        var w = new TransportTimingWindow(1.0, 100);
        string header = w.Header(Utc, 0.25, 0.2502, "System.Diagnostics.Stopwatch", 10_000_000, 42);
        Check(Has(header, "\"kind\":\"header\"") && Has(header, "\"mono_before_utc_s\":0.25") && Has(header, "\"mono_after_utc_s\":0.2502")
              && Has(header, "\"mono_origin_ticks\":42") && w.Records == 1, "Header brackets its UTC read with monotonic times");
        Check(Has(header, "\"queue_full_prefix\":\"" + TransportTimingWindow.QueueFullPrefix + "\"")
              && Has(header, "not proof that nothing was dropped") && Has(header, "not counts of dropped messages")
              && Has(header, "not an atomic pair"), "Header states exact warning prefix and count semantics");
        Check(Has(header, "\"nominal_exhaustion_after_first_sample_s\":99") && Has(header, "No synchronization with ROS")
              && Has(header, "can step") && Has(header, "no resume"), "Header states coverage, clock-step and cross-host limits");

        // Steady 60 Hz cadence: one record per reporting second, never per frame.
        int due = 0;
        for (int i = 0; i <= 210; i++)
            if (w.Sample(i / 60.0, i * 0.01, false)) { due++; Emit(w); }
        Check(due == 3 && w.Records == 4, "60 Hz for 3.5 s emits exactly three periodic records");
        Check(Math.Abs(w.CumulativeMaxFrameGap - 1 / 60.0) < 1e-9 && w.TotalFrames == 211, "Steady cadence max gap is one frame");

        // A hitch that straddles a reporting boundary is kept in its window and in the cumulative maximum.
        w = Fresh();
        double lastBefore = 0;
        for (int i = 0; i / 60.0 < .99; i++) { lastBefore = i / 60.0; w.Sample(lastBefore, lastBefore, false); }
        string hitchGap = R(1.9 - lastBefore);
        bool dueAfterHitch = w.Sample(1.9, 1.9, false);
        string hitch = Emit(w);
        Check(dueAfterHitch && Has(hitch, "\"window_max_frame_gap_s\":" + hitchGap + ","), "Hitch across boundary is reported exactly in the window it ends");
        for (int i = 1; 1.9 + i / 60.0 < 3.0; i++)
            if (w.Sample(1.9 + i / 60.0, 1.9 + i / 60.0, false)) hitch = Emit(w);
        Check(Has(hitch, "\"cumulative_max_frame_gap_s\":" + hitchGap + ",") && !Has(hitch, "\"window_max_frame_gap_s\":" + hitchGap + ","),
              "Later window keeps the cumulative hitch but its own small window gap");

        // Paused or zero simulation time is reported as such, not inferred from wall time.
        w = Fresh();
        string paused = null;
        for (int i = 0; i <= 70; i++) if (w.Sample(i / 60.0, 12.5, false)) paused = Emit(w);
        Check(Has(paused, "\"sim_time_start_s\":12.5") && Has(paused, "\"sim_time_end_s\":12.5"), "Paused sim time stays constant in the record");

        // Queue-full lines: per-record delta, running total, cumulative observation time, negative deltas ignored.
        w = Fresh();
        w.Sample(0, 0, false); w.Sample(1, 1, false);
        string first = Emit(w, 5, .75, true);
        w.Sample(2, 2, false);
        string second = Emit(w, -3, .75);
        Check(Has(first, "\"queue_full_lines_since_previous_record\":5") && Has(first, "\"queue_full_lines_total\":5")
              && Has(first, "\"cumulative_last_queue_full_observed_mono_s\":0.75") && Has(first, "\"connection_error\":true")
              && Has(first, "\"utc\":\"" + Utc + "\",\"mono_before_utc_s\":5,\"mono_after_utc_s\":5.001"),
              "Warning lines, cumulative observation time, connection status and UTC bracket are recorded");
        Check(Has(second, "\"queue_full_lines_since_previous_record\":0") && Has(second, "\"queue_full_lines_total\":5")
              && Has(second, "\"cumulative_last_queue_full_observed_mono_s\":0.75"),
              "Negative deltas cannot reduce totals; the last observation time is cumulative, not window-attributed");

        // Lifecycle discontinuity: stopping ends coverage permanently, so a suspension is never a frame gap.
        w = Fresh();
        for (int i = 0; i <= 30; i++) w.Sample(i / 60.0, i / 60.0, false);
        string stop = w.Stop("component disabled", Utc, 6, 6.0005, 2, .3, false);
        Check(Has(stop, "\"kind\":\"stopped\"") && Has(stop, "coverage ended: component disabled")
              && Has(stop, "\"frames\":31") && Has(stop, "\"queue_full_lines_since_previous_record\":2") && w.Ended,
              "Stop emits one labelled final record with the partial window");
        double maxBefore = w.CumulativeMaxFrameGap;
        Check(!w.Sample(100.0, 100.0, false) && w.CumulativeMaxFrameGap == maxBefore && w.TotalFrames == 31,
              "After stop a later frame is not sampled, so suspension never becomes a frame gap");
        Check(Emit(w) == null && w.Stop("again", Utc, 7, 7, 0, double.NaN, false) == null, "No record after stop; stop is idempotent");

        // Record cap: header + windows + one labelled exhaustion record, then nothing.
        w = Fresh(3);
        w.Sample(0, 0, false); w.Sample(1, 1, false);
        string window = Emit(w);
        w.Sample(2, 2, false);
        string exhausted = Emit(w);
        Check(Has(window, "\"kind\":\"window\"") && Has(exhausted, "\"kind\":\"exhausted\"") && Has(exhausted, "tracing stopped"),
              "Last capped record is labelled exhausted");
        Check(w.Exhausted && w.Ended && !w.Sample(3, 3, false) && Emit(w, 1, 0) == null && w.Records == 3
              && w.Stop("late", Utc, 9, 9, 0, double.NaN, false) == null, "Nothing is sampled, emitted or stopped after exhaustion");

        // Invalid configuration and samples.
        bool Throws(Action action) { try { action(); return false; } catch (ArgumentOutOfRangeException) { return true; } }
        Check(Throws(() => new TransportTimingWindow(0)) && Throws(() => new TransportTimingWindow(double.NaN))
              && Throws(() => new TransportTimingWindow(double.PositiveInfinity)) && Throws(() => new TransportTimingWindow(1, 1)),
              "Invalid interval and cap are rejected");
        w = Fresh(10);
        Check(!w.Sample(double.NaN, 0, false) && w.TotalFrames == 0, "Non-finite monotonic samples are ignored");
        bool headerTwice = false;
        try { w.Header(Utc, 0, 0, "Stopwatch", 1, 0); } catch (InvalidOperationException) { headerTwice = true; }
        Check(headerTwice, "Header cannot be written twice");
        Check(Has(new TransportTimingWindow().Header(Utc, 0, 0, "a\"b", 1, 0), "a\\\"b"), "Text fields are JSON escaped");

        // Schema v3: independent FixedUpdate stream and per-sample connection-error reads (binary-exact times).
        Check(Has(header, "\"schema\":\"igvc_transport_timing_v3\"") && Has(header, "Two independent sample streams")
              && Has(header, "not exact intervals or durations") && Has(header, "not a unique main-thread cause")
              && Has(header, "unavailable, not healthy"), "v3 header labels both sample streams and their limits");
        w = Fresh();
        string v3 = null;
        for (int i = 0; i <= 8; i++)
        {
            for (int j = Math.Max(0, 2 * i - 1); j <= 2 * i; j++) w.SampleFixed(j * 0.0625, j * 0.0625, j == 7);
            if (w.Sample(i * 0.125, i * 0.125, i >= 3 && i <= 5)) v3 = Emit(w);
        }
        Check(Has(v3, "\"connection_error\":false") && Has(v3, "\"update_error_samples\":3,") && Has(v3, "\"total_update_error_samples\":3,"),
              "Subsecond error samples invisible to the record-time read are counted");
        Check(Has(v3, "\"fixed_samples\":17,") && Has(v3, "\"fixed_error_samples\":1,") && Has(v3, "\"fixed_first_mono_s\":0,")
              && Has(v3, "\"fixed_last_mono_s\":1,") && Has(v3, "\"window_max_fixed_gap_s\":0.0625,")
              && Has(v3, "\"window_max_fixed_gap_end_mono_s\":0.0625,") && Has(v3, "\"fixed_sim_time_end_s\":1"),
              "Several fixed ticks per Update are counted with their largest gap and its end time");
        string noFixed = null;
        for (int i = 9; i <= 16; i++) if (w.Sample(i * 0.125, i * 0.125, false)) noFixed = Emit(w);
        Check(Has(noFixed, "\"fixed_samples\":0,") && Has(noFixed, "\"fixed_first_mono_s\":null") && Has(noFixed, "\"window_max_fixed_gap_s\":null")
              && Has(noFixed, "\"cumulative_last_fixed_mono_s\":1,") && Has(noFixed, "\"cumulative_max_fixed_gap_s\":0.0625,")
              && Has(noFixed, "\"update_error_samples\":0,") && Has(noFixed, "\"total_update_error_samples\":3,"),
              "A window without fixed samples reports them unavailable and keeps the open gap's start");
        string spanned = null;
        for (int i = 17; i <= 24; i++)
        {
            if (i == 20) w.SampleFixed(2.5, 2.5, false);
            if (w.Sample(i * 0.125, i * 0.125, false)) spanned = Emit(w);
        }
        Check(Has(spanned, "\"fixed_samples\":1,") && Has(spanned, "\"total_fixed_samples\":18,") && Has(spanned, "\"window_max_fixed_gap_s\":1.5,")
              && Has(spanned, "\"window_max_fixed_gap_end_mono_s\":2.5,") && Has(spanned, "\"cumulative_max_fixed_gap_s\":1.5,")
              && Has(spanned, "\"window_start_mono_s\":2,"), "A fixed gap spanning a boundary is kept whole in the record where it ends");
        w.SampleFixed(3.25, 3.25, true);
        string partial = w.Stop("component disabled", Utc, 6, 6, 0, double.NaN, false);
        Check(Has(partial, "\"kind\":\"stopped\"") && Has(partial, "\"fixed_samples\":1,") && Has(partial, "\"window_max_fixed_gap_s\":0.75,")
              && Has(partial, "\"cumulative_max_fixed_gap_s\":1.5,\"cumulative_max_fixed_gap_end_mono_s\":2.5,")
              && Has(partial, "\"total_fixed_samples\":19,") && Has(partial, "\"total_fixed_error_samples\":2,"),
              "Final partial window carries its fixed samples without losing or double counting");
        w.SampleFixed(4, 4, true);
        Check(w.TotalFixedSamples == 19 && w.CumulativeMaxFixedGap == 1.5, "No fixed sample is taken after stop");
        w = Fresh(3);
        w.Sample(0, 0, false); w.Sample(1, 1, false); Emit(w); w.Sample(2, 2, false); Emit(w);
        w.SampleFixed(3, 3, false);
        Check(w.Exhausted && w.TotalFixedSamples == 0, "No fixed sample is taken after exhaustion");
        w = Fresh();
        string none = w.Stop("component destroyed", Utc, 1, 1, 0, double.NaN, false);
        Check(Has(none, "\"fixed_samples\":0,") && Has(none, "\"total_fixed_samples\":0,") && Has(none, "\"cumulative_last_fixed_mono_s\":null")
              && Has(none, "\"cumulative_max_fixed_gap_s\":null") && Has(none, "\"fixed_sim_time_start_s\":null"),
              "With no fixed samples every fixed timing field is null, never zero");
        w = Fresh();
        w.SampleFixed(double.PositiveInfinity, 0, true);
        Check(w.TotalFixedSamples == 0, "Non-finite fixed samples are ignored");
        return count;
    }
}
