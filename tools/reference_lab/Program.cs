using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;
using System.IO.Compression;
using IGVC.Reference;
#if !REFLAB_ONLY_PATHFINDING && !REFLAB_ONLY_VEHICLES
using IGVC.Reference.Teacher;
#endif

// Offline Reference Lab harness. `check [--course course.json]` runs every model check;
// course geometry is WORLD data and is used here only for reference/audit studies.
public static class Program
{
    private const string FrozenCourse = "artifacts/sandbox/runs/20261002T035715-45c98a0f/course.json";
    private const string RealRun = "artifacts/sandbox/runs/20261002T061204-d4510a99";
    private const string Usage = "usage: check [--course course.json] [--real-run <run-folder>] [--keep-going] | label (--run <run-folder> | --runs <dir-or-glob>) [--out <dir>] [--horizon 5] [--ceilings 0.6,2.2] [--corridor-label straight-v1|path-v3]";

    public static int Main(string[] args)
    {
        string command = args.Length > 0 ? args[0] : "check";
        string course = Option(args, "--course", null);
        if (course == null)
        {
            string root = FindRoot();
            string frozen = root == null ? null : Path.Combine(root, FrozenCourse);
            if (frozen != null && File.Exists(frozen)) course = frozen;
        }
#if !REFLAB_ONLY_PATHFINDING && !REFLAB_ONLY_VEHICLES
        if (command == "label") return Label(args);
#endif
        if (command != "check") { Console.Error.WriteLine(Usage); return 2; }
#if !REFLAB_ONLY_PATHFINDING && !REFLAB_ONLY_VEHICLES
        string realRun = Option(args, "--real-run", FindRoot() == null ? null : Path.Combine(FindRoot(), RealRun));
        TeacherChecks.RunLoader = LoadRun; TeacherChecks.RealRunDir = realRun;
#endif
        var context = new CheckContext { Log = Console.WriteLine, StopOnFailure = !args.Contains("--keep-going") };
        if (course != null) { context.Course = LoadCourse(course); Console.WriteLine("course " + course); }
        var watch = System.Diagnostics.Stopwatch.StartNew();
        try { ReferenceChecks.RunAll(context); }
        catch (Exception e) { if (!e.Message.StartsWith("FAIL ")) { context.Failures.Add("exception"); Console.WriteLine("ERROR " + e); } }
        Console.WriteLine($"REFERENCE_LAB_CHECKS passed={context.Passed} failed={context.Failures.Count} seconds={watch.Elapsed.TotalSeconds:0.0}");
        return context.Failures.Count == 0 ? 0 : 1;
    }
    private static bool Contains(this string[] a, string v) => Array.IndexOf(a, v) >= 0;
    private static string Option(string[] args, string name, string fallback)
    {
        int i = Array.IndexOf(args, name);
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : fallback;
    }
    private static string FindRoot()
    {
        for (var d = new DirectoryInfo(AppContext.BaseDirectory); d != null; d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "AGENTS.md"))) return d.FullName;
        for (var d = new DirectoryInfo(Directory.GetCurrentDirectory()); d != null; d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "AGENTS.md"))) return d.FullName;
        return null;
    }
#if !REFLAB_ONLY_PATHFINDING && !REFLAB_ONLY_VEHICLES
    // ---- label: offline hindsight teacher. Output only under artifacts/learning/labels/<run>/ (git-ignored);
    // the labels are WORLD-derived and must never be written where the mission reads.
    private static int Label(string[] args)
    {
        string one = Option(args, "--run", null), many = Option(args, "--runs", null), outDir = Option(args, "--out", null), root = FindRoot();
        if (one == null && many == null) { Console.Error.WriteLine(Usage); return 2; }
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var options = new LabelOptions { HorizonS = double.Parse(Option(args, "--horizon", "5"), inv) };
        string ceilings = Option(args, "--ceilings", null);
        if (ceilings != null) options.SpeedCeilings = Array.ConvertAll(ceilings.Split(','), s => double.Parse(s, inv));
        // Corridor label mode: straight-v1 (default, legacy fields only) or path-v3 (adds separate corridor_target fields;
        // legacy fields unchanged). path-v3 must name its own --out root (e.g. artifacts/learning/labels-path-v3).
        options.CorridorCost = Option(args, "--corridor-label", LabelOptions.StraightV1);
        if (options.CorridorCost != LabelOptions.PathV3 && options.CorridorCost != LabelOptions.StraightV1) { Console.Error.WriteLine(Usage); return 2; }
        // path-v3 has no default output: it must name its own root, never inside the legacy artifacts/learning/labels.
        string legacyRoot = Path.GetFullPath(Path.Combine(root ?? ".", "artifacts", "learning", "labels"));
        if (options.CorridorCost == LabelOptions.PathV3 && (outDir == null || (Path.GetFullPath(outDir).TrimEnd('\\', '/') + Path.DirectorySeparatorChar).StartsWith(legacyRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)))
        { Console.Error.WriteLine("--corridor-label path-v3 requires --out outside " + legacyRoot); return 2; }
        var runs = new List<string>();
        if (one != null) runs.Add(Path.GetFullPath(one));
        else
        {
            string full = Path.GetFullPath(many);
            if (File.Exists(Path.Combine(full, "run.json"))) runs.Add(full);
            else if (Directory.Exists(full)) runs.AddRange(Directory.GetDirectories(full));
            else runs.AddRange(Directory.GetDirectories(Path.GetDirectoryName(full), Path.GetFileName(full)));
            runs.RemoveAll(d => !File.Exists(Path.Combine(d, "run.json")) || !File.Exists(Path.Combine(d, "course.json")) || !Directory.Exists(Path.Combine(d, "decisions")));
            runs.Sort(StringComparer.Ordinal);
        }
        var teachers = new Dictionary<string, HindsightTeacher>(); int failed = 0;
        foreach (string dir in runs)
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                // Output state is checked before any work; run.Name is the folder name.
                string target = one != null && outDir != null ? outDir : Path.Combine(outDir ?? Path.Combine(root ?? ".", "artifacts", "learning", "labels"), new DirectoryInfo(dir).Name);
                string refusal = OutputRefusal(target);
                if (refusal != null) throw new InvalidOperationException("refusing to write " + options.CorridorCost + " labels to " + target + ": " + refusal + "; outputs are immutable, label into a fresh --out directory");
                var run = LoadRun(dir);
                if (!teachers.TryGetValue(run.Course.Identity, out var teacher)) teachers[run.Course.Identity] = teacher = new HindsightTeacher(run.Course);
                var res = new Labeler(teacher, options).Label(run);
                Directory.CreateDirectory(target);
                File.WriteAllText(Path.Combine(target, "labels.jsonl"), string.Join("\n", res.Lines) + "\n");
                File.WriteAllText(Path.Combine(target, "summary.json"), res.Summary + "\n");
                File.WriteAllText(Path.Combine(target, "traps.json"), res.TrapsJson + "\n");
                var plan = res.Labels.ConvertAll(l => l.RegretVsTeacherM).FindAll(v => !double.IsNaN(v));
                double mean = 0, max = double.NaN; foreach (var v in plan) { mean += v / plan.Count; max = double.IsNaN(max) ? v : Math.Max(max, v); }
                Console.WriteLine(FormattableString.Invariant($"LABELLED {run.Name} snapshots={run.Snapshots.Count} labelled={res.Labels.Count} outcomes=v{(run.OutcomeSchema == 2 ? 2 : 1)} reachable={res.AllReachable} goal_mismatch_max={res.MaxMismatch:0.000}m plan_regret_mean={mean:0.00}m max={max:0.00}m traps={res.Traps.Count} status={run.Status} corridor_label={options.CorridorCost} corridor={res.CorridorCandidates} line_of_sight={res.Count(Labeler.LineOfSight)} grid_path={res.Count(Labeler.GridPath)} unavailable={res.CorridorCandidates - res.Count(Labeler.LineOfSight) - res.Count(Labeler.GridPath)} expanded={res.CorridorExpanded} seconds={watch.Elapsed.TotalSeconds:0.0} -> {target}"));
                foreach (var t in res.Traps) Console.WriteLine("  TRAP " + Labeler.Describe(t));
            }
            catch (Exception e) { failed++; Console.WriteLine($"FAILED {dir}: {e.Message}"); }
        }
        Console.WriteLine($"LABEL_RUNS done={runs.Count - failed} failed={failed}");
        return failed == 0 && runs.Count > 0 ? 0 : 1;
    }

    private static double D(JsonElement e) => e.ValueKind == JsonValueKind.Number ? e.GetDouble() : double.NaN;
    /// <summary>Null when target is fresh: absent, or a directory holding none of the generated names. Generated output is
    /// immutable: if summary.json, labels.jsonl or traps.json exists (as file or directory) the target is refused whatever
    /// its mode or completeness; contents are never inspected. Unrelated files are left alone. Assumes one serial writer.</summary>
    private static string OutputRefusal(string target)
    {
        if (File.Exists(target)) return "target is a file";
        if (!Directory.Exists(target)) return null;
        foreach (string name in new[] { "summary.json", "labels.jsonl", "traps.json" })
        {
            string p = Path.Combine(target, name);
            if (File.Exists(p) || Directory.Exists(p)) return "generated output " + name + " already exists";
        }
        return null;
    }
    private static bool Has(JsonElement e, string name, out JsonElement v) { v = default; return e.ValueKind == JsonValueKind.Object && e.TryGetProperty(name, out v) && v.ValueKind != JsonValueKind.Null; }
    private static V2 Pt(JsonElement e) => new V2(D(e[0]), D(e[1]));
    private static List<V2> Pts(JsonElement e) { var l = new List<V2>(); foreach (var p in e.EnumerateArray()) l.Add(Pt(p)); return l; }
    private static CandidateIn Candidate(JsonElement e, string endpointKey)
    {
        if (e.ValueKind != JsonValueKind.Object || !Has(e, endpointKey, out var end)) return null;
        var c = new CandidateIn { End = Pt(end), Yaw = end.GetArrayLength() > 2 ? D(end[2]) : double.NaN };
        if (Has(e, "path", out var path)) c.Path = Pts(path);
        if (Has(e, "path_length_m", out var len)) c.PathLength = D(len);
        if (Has(e, "score", out var score)) c.Score = D(score);
        if (Has(e, "source", out var src)) c.Source = src.GetString();
        return c;
    }

    /// <summary>Reads a finished run folder (read-only): course, autonomy goals, trajectory, v1 events, snapshots, optional v2 outcomes.</summary>
    public static RunIn LoadRun(string dir)
    {
        var run = new RunIn { Name = new DirectoryInfo(dir).Name, Course = LoadCourse(Path.Combine(dir, "course.json")) };
        string auto = Path.Combine(dir, "autonomy.json");
        if (File.Exists(auto))
        {
            using var a = JsonDocument.Parse(File.ReadAllBytes(auto));
            var o = a.RootElement.GetProperty("origin");
            run.Origin = new GeoOrigin { Latitude = o.GetProperty("latitude").GetDouble(), Longitude = o.GetProperty("longitude").GetDouble(), Altitude = Has(o, "altitude", out var al) ? D(al) : 0 };
            foreach (var g in a.RootElement.GetProperty("goals").EnumerateArray())
                run.Goals.Add(Geo.ToOdom(run.Origin, g.GetProperty("latitude").GetDouble(), g.GetProperty("longitude").GetDouble(), Has(g, "altitude", out var ga) ? D(ga) : 0));
        }
        var evaluated = new Dictionary<int, JsonElement>(); var admitted = new Dictionary<int, bool>(); var sent = new HashSet<int>();
        using var r = JsonDocument.Parse(File.ReadAllBytes(Path.Combine(dir, "run.json")));
        var root = r.RootElement;
        if (Has(root, "status", out var st)) run.Status = st.GetString();
        if (Has(root, "reason", out var rs)) run.Reason = rs.ValueKind == JsonValueKind.String ? rs.GetString() : rs.ToString();
        if (Has(root, "trajectory", out var traj))
        {
            int n = traj.GetArrayLength(); run.TrajT = new double[n]; run.TrajP = new V2[n]; run.TrajYaw = new double[n]; int i = 0;
            foreach (var row in traj.EnumerateArray()) { run.TrajT[i] = D(row[0]); run.TrajP[i] = new V2(D(row[1]), D(row[2])); run.TrajYaw[i] = D(row[3]); i++; }
        }
        if (Has(root, "decisions", out var events))
            foreach (var e in events.EnumerateArray())
            {
                if (!Has(e, "sequence", out var sq) || !Has(e, "phase", out var ph)) continue;
                int seq = sq.GetInt32(); string phase = ph.GetString();
                if (phase == "evaluated") evaluated[seq] = e;
                else if (phase == "path_entry" && Has(e, "admission", out var adm) && Has(adm, "accepted", out var acc) && (acc.ValueKind == JsonValueKind.True || acc.ValueKind == JsonValueKind.False)) admitted[seq] = acc.GetBoolean();
                else if (phase == "sent_goal") sent.Add(seq);
            }
        var outcomes = new Dictionary<int, JsonElement>();
        string outcomesPath = Path.Combine(dir, "decisions", "outcomes.jsonl");
        if (File.Exists(outcomesPath))
        {
            foreach (string line in File.ReadAllLines(outcomesPath))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                using var d = JsonDocument.Parse(line);
                if (Has(d.RootElement, "index", out var ix)) outcomes[ix.GetInt32()] = d.RootElement.Clone();
            }
            if (outcomes.Count > 0) run.OutcomeSchema = 2;
        }
        var files = Directory.GetFiles(Path.Combine(dir, "decisions"), "*.json.gz"); Array.Sort(files, StringComparer.Ordinal);
        foreach (string file in files)
        {
            if (!int.TryParse(Path.GetFileName(file).Split('.')[0], out int index)) continue;
            byte[] raw;
            using (var gz = new GZipStream(File.OpenRead(file), CompressionMode.Decompress)) using (var ms = new MemoryStream()) { gz.CopyTo(ms); raw = ms.ToArray(); }
            using var doc = JsonDocument.Parse(raw);
            var input = doc.RootElement.GetProperty("input"); var meta = doc.RootElement.GetProperty("metadata");
            var s = new SnapshotIn { Index = index, Robot = Pt(input.GetProperty("robot_xy")), Yaw = D(input.GetProperty("robot_yaw")), Destination = Pt(input.GetProperty("destination")) };
            if (Has(meta, "destination_index", out var di)) s.DestinationIndex = di.GetInt32();
            if (Has(meta, "odom_stamp_ns", out var os)) s.StampS = os.GetDouble() * 1e-9;
            if (Has(input, "planner_options", out var po) && Has(po, "lookahead", out var la)) s.Lookahead = D(la);
            if (outcomes.TryGetValue(index, out var oc))
            {
                if (Has(oc, "plan", out var plan)) { s.Plan = Candidate(plan, "endpoint"); if (s.Plan != null && s.Plan.Source == "") s.Plan.Source = "plan"; }
                if (Has(oc, "candidates", out var cands)) { s.Candidates = new List<CandidateIn>(); foreach (var c in cands.EnumerateArray()) { var ci = Candidate(c, "endpoint"); if (ci != null) s.Candidates.Add(ci); } }
                if (Has(oc, "action", out var ac)) s.Action = ac.GetString();
                if (Has(oc, "admitted", out var ad)) s.Admitted = ad.GetBoolean() ? 1 : 0;
                if (Has(oc, "robot_xy_after", out var af)) { s.HasAfter = true; s.After = Pt(af); }
                if (Has(oc, "progress_m", out var pg)) s.ProgressM = D(pg);
                if (Has(oc, "search_wall_s", out var sw)) s.SearchWallS = D(sw);
            }
            else
            {
                if (evaluated.TryGetValue(index, out var ev) && Has(ev, "plan", out var plan))
                {
                    s.Plan = Candidate(plan, "local_goal");
                    if (s.Plan != null) { s.Plan.Source = "v1_evaluated_plan"; if (Has(plan, "yaw", out var py)) s.Plan.Yaw = D(py); }
                }
                if (admitted.TryGetValue(index, out bool ok)) s.Admitted = ok ? 1 : 0;
                s.Action = s.Plan == null ? "no_plan" : sent.Contains(index) ? "sent_goal" : s.Admitted == 0 ? "rejected" : "evaluated";
            }
            run.Snapshots.Add(s);
        }
        return run;
    }
#endif

    public static CourseGeometry LoadCourse(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        using var doc = JsonDocument.Parse(bytes);
        var r = doc.RootElement;
        var center = new List<V2>(); var hw = new List<double>(); var painted = new List<bool>();
        foreach (var p in r.GetProperty("centerline").EnumerateArray())
        { center.Add(new V2(p.GetProperty("x").GetDouble(), p.GetProperty("y").GetDouble())); hw.Add(p.GetProperty("half_width").GetDouble()); painted.Add(p.GetProperty("painted").GetBoolean()); }
        var obstacles = new List<CourseObstacle>();
        foreach (var o in r.GetProperty("obstacles").EnumerateArray())
            obstacles.Add(new CourseObstacle { Id = o.GetProperty("id").GetString(), Kind = o.GetProperty("kind").GetString(), X = o.GetProperty("x").GetDouble(), Y = o.GetProperty("y").GetDouble(), Yaw = o.GetProperty("yaw").GetDouble(), Length = o.GetProperty("length").GetDouble(), Width = o.GetProperty("width").GetDouble() });
        RampInfo ramp = null;
        if (r.TryGetProperty("ramps", out var ramps) && ramps.GetArrayLength() > 0)
        {
            var a = ramps[0];
            ramp = new RampInfo { X = a.GetProperty("x").GetDouble(), Y = a.GetProperty("y").GetDouble(), Yaw = a.GetProperty("yaw").GetDouble(), Width = a.GetProperty("width").GetDouble(), RiseLength = a.GetProperty("rise_length").GetDouble(), DeckLength = a.GetProperty("deck_length").GetDouble(), Height = a.GetProperty("height").GetDouble() };
        }
        string hash = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        return CourseGeometry.Create(center, hw, painted, r.GetProperty("lane_width_m").GetDouble(), obstacles, ramp, r.GetProperty("seed").GetInt32(), "seed " + r.GetProperty("seed").GetInt32() + " sha256:" + hash.Substring(0, 12));
    }
}
