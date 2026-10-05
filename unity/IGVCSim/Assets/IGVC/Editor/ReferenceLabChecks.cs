using System;
using System.IO;
using IGVC;
using IGVC.Reference;
using UnityEngine;

// Runs the engine-free Reference Lab model checks inside Unity (same source as tools/reference_lab).
public static class ReferenceLabChecks
{
    private const string FrozenCourse = "artifacts/sandbox/runs/20261002T035715-45c98a0f/course.json";

    [UnityEditor.MenuItem("IGVC/Run Reference Lab Checks")]
    public static void Run()
    {
        var context = new CheckContext { Log = Debug.Log };
        string course = Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", FrozenCourse));
        if (File.Exists(course)) context.Course = ReferenceLab.FromManifest(CourseVariant.Read(course));
        context.Check(Shader.Find("IGVC/ReferenceOverlay") != null, "overlay shader is available to Shader.Find");
        context.Check(string.IsNullOrEmpty(LayerMask.LayerToName(ReferenceLayer.Index)), "reference layer index is not used by a named project layer");
        ReferenceChecks.RunAll(context);
        Debug.Log("IGVC_REFERENCE_CHECKS_OK passed=" + context.Passed);
    }
}
