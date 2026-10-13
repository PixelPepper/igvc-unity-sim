using System;
using UnityEditor;
using UnityEngine;

// Build-time realistic materials for the reference-map drive scene (T-0090), adapted from the parked
// sim-realism RealismAssets. CC0 textures (ambientCG, see Assets/IGVC/Realism/LICENSE.md) are read-only
// inputs; materials are saved as assets under Assets/IGVC/Realism/Materials so the scene references them
// directly (the build then includes the Standard and Skybox/Procedural shaders it uses). No project-wide
// graphics settings are changed: the drive scene uses no fog.
public static class RealismAssets
{
    private const string Textures = "Assets/IGVC/Realism/Textures/";
    private const string Output = "Assets/IGVC/Realism/Materials/";

    public static void ConfigureTextures()
    {
        foreach (var name in new[] { "Asphalt031", "Asphalt033", "Grass004" })
        {
            void Set(string file, Action<TextureImporter> configure)
            {
                string path = Textures + name + "/" + file;
                AssetDatabase.ImportAsset(path);
                var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                if (importer == null) throw new Exception("Realism texture missing: " + path);
                importer.wrapMode = TextureWrapMode.Repeat; importer.anisoLevel = 8; importer.maxTextureSize = 1024;
                configure(importer); importer.SaveAndReimport();
            }
            Set("Albedo.jpg", i => { i.textureType = TextureImporterType.Default; i.sRGBTexture = true; });
            Set("Normal.jpg", i => { i.textureType = TextureImporterType.NormalMap; });
            Set("MetallicSmoothness.png", i => { i.textureType = TextureImporterType.Default; i.sRGBTexture = false; i.alphaSource = TextureImporterAlphaSource.FromInput; });
            Set("Occlusion.jpg", i => { i.textureType = TextureImporterType.Default; i.sRGBTexture = false; });
        }
        AssetDatabase.Refresh();
    }

    private static Shader Find(string name)
    {
        var shader = Shader.Find(name);
        if (shader == null) throw new Exception("Built-in shader missing: " + name);
        return shader;
    }

    // Create or update a material asset in place (keeps its GUID).
    private static Material Asset(string name, string shader, Action<Material> configure)
    {
        System.IO.Directory.CreateDirectory(Output);
        string path = Output + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null) { material = new Material(Find(shader)); AssetDatabase.CreateAsset(material, path); }
        else material.shader = Find(shader);
        configure(material); EditorUtility.SetDirty(material);
        return material;
    }

    // Textured asphalt tiled every 3 m over a ground of the given size (world-metre texture scale).
    public static Material Asphalt(Vector2 groundSize)
    {
        Texture2D Load(string file)
        {
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(Textures + "Asphalt031/" + file);
            if (t == null) throw new Exception("Realism texture not imported: Asphalt031/" + file);
            return t;
        }
        return Asset("ReferenceAsphalt", "Standard", m =>
        {
            m.SetTexture("_MainTex", Load("Albedo.jpg"));
            m.SetTexture("_BumpMap", Load("Normal.jpg")); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", Load("MetallicSmoothness.png")); m.SetFloat("_GlossMapScale", 1f); m.EnableKeyword("_METALLICGLOSSMAP");
            m.SetTexture("_OcclusionMap", Load("Occlusion.jpg")); m.SetFloat("_OcclusionStrength", .8f);
            m.mainTextureScale = groundSize / 3f;
            m.color = new Color(.55f, .55f, .55f, 1);   // Asphalt031's albedo is concrete-light
        });
    }

    public static Material Lit(string name, Color color, float smoothness) =>
        Asset(name, "Standard", m => { m.color = color; m.SetFloat("_Glossiness", smoothness); m.SetFloat("_Metallic", 0); });

    public static Material Sky() => Asset("ReferenceSky", "Skybox/Procedural", m =>
    {
        m.SetFloat("_SunSize", .04f); m.SetColor("_SkyTint", new Color(.5f, .55f, .62f));
        m.SetColor("_GroundColor", new Color(.36f, .37f, .36f)); m.SetFloat("_Exposure", 1.25f); m.SetFloat("_AtmosphereThickness", .9f);
    });
}
