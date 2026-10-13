using System;
using System.Globalization;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

namespace IGVC
{
    // Scene-local visual conditions for the reference-map drive player (T-0090). Explicit presets only, chosen
    // with --reference-conditions clear-noon|overcast|low-sun (default clear-noon); no randomness, rain, fog,
    // physics or sensor-noise changes. Runs in Awake, before TransportProbe.Start creates its sensors, and
    // writes the applied settings to --reference-run-dir/reference-conditions.json when given. Only the RGB
    // sensor and spectator cameras get the sky; the depth camera keeps TransportProbe's own settings.
    [DefaultExecutionOrder(-1000)]
    public sealed class ReferenceDriveConditions : MonoBehaviour
    {
        [SerializeField] private Light sun;
        [SerializeField] private Material sky;
        [SerializeField] private Camera[] skyCameras;

        [Serializable] public sealed class Applied
        {
            public string preset; public float sun_elevation_deg, sun_azimuth_deg, sun_intensity, shadow_strength;
            public Color sun_color, ambient_sky; public float sky_exposure, sky_atmosphere_thickness;
        }

        public void Configure(Light light, Material skyMaterial, Camera[] cameras) { sun = light; sky = skyMaterial; skyCameras = cameras; }

        public static Applied Preset(string name)
        {
            switch (name)
            {
                case "clear-noon": return new Applied { preset = name, sun_elevation_deg = 60, sun_azimuth_deg = 200, sun_intensity = 1.2f, shadow_strength = .85f,
                    sun_color = new Color(1f, .96f, .9f), ambient_sky = new Color(.38f, .5f, .7f), sky_exposure = 1.25f, sky_atmosphere_thickness = .9f };
                case "overcast": return new Applied { preset = name, sun_elevation_deg = 45, sun_azimuth_deg = 150, sun_intensity = .35f, shadow_strength = .15f,
                    sun_color = new Color(.85f, .87f, .9f), ambient_sky = new Color(.62f, .64f, .67f), sky_exposure = 1.6f, sky_atmosphere_thickness = .4f };
                case "low-sun": return new Applied { preset = name, sun_elevation_deg = 12, sun_azimuth_deg = 260, sun_intensity = .7f, shadow_strength = .85f,
                    sun_color = new Color(1f, .72f, .48f), ambient_sky = new Color(.33f, .4f, .55f), sky_exposure = 1.1f, sky_atmosphere_thickness = 1.1f };
                default: throw new ArgumentException("Unknown --reference-conditions preset (clear-noon, overcast, low-sun): " + name);
            }
        }

        private static string Arg(string name, string fallback)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i + 1 < args.Length; i++) if (args[i] == name) return args[i + 1];
            return fallback;
        }

        private void Awake() => Apply(Arg("--reference-conditions", "clear-noon"), Arg("--reference-run-dir", ""));

        // Applies one explicit preset; also used by the editor checks for their capture renders.
        public Applied Apply(string presetName, string runDirectory)
        {
            var applied = Preset(presetName);
            if (sun == null) throw new InvalidOperationException("Reference drive sun missing; rebuild the scene");
            sun.transform.rotation = Quaternion.Euler(applied.sun_elevation_deg, applied.sun_azimuth_deg, 0);
            sun.color = applied.sun_color; sun.intensity = applied.sun_intensity;
            sun.shadows = LightShadows.Soft; sun.shadowStrength = applied.shadow_strength;
            if (Application.isPlaying) QualitySettings.shadowDistance = 45;   // never alter project quality settings in the editor
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = applied.ambient_sky;
            RenderSettings.ambientEquatorColor = Color.Lerp(applied.ambient_sky, new Color(.55f, .52f, .48f), .5f);
            RenderSettings.ambientGroundColor = new Color(.2f, .2f, .19f);
            RenderSettings.fog = false;   // no fog: keeps depth and RGB free of fog variants and contamination
            if (sky != null)
            {
                var instance = new Material(sky);
                instance.SetFloat("_Exposure", applied.sky_exposure);
                instance.SetFloat("_AtmosphereThickness", applied.sky_atmosphere_thickness);
                RenderSettings.skybox = instance; RenderSettings.sun = sun;
                if (skyCameras != null) foreach (var c in skyCameras) if (c != null) c.clearFlags = CameraClearFlags.Skybox;
            }
            if (!string.IsNullOrEmpty(runDirectory))
            {
                Directory.CreateDirectory(runDirectory);
                File.WriteAllText(Path.Combine(runDirectory, "reference-conditions.json"), JsonUtility.ToJson(applied, true));
            }
            Debug.Log(string.Format(CultureInfo.InvariantCulture, "IGVC_REFERENCE_CONDITIONS preset={0} elev={1} az={2}",
                applied.preset, applied.sun_elevation_deg, applied.sun_azimuth_deg));
            return applied;
        }
    }
}
