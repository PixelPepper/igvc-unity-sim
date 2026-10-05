using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace IGVC.Reference
{
    /// <summary>
    /// Reference drawings live on their own layer with no colliders: lidar raycasts use layer 0 only and
    /// TransportProbe removes this layer from the RGB/depth sensor cameras, so sensors never observe them.
    /// </summary>
    public static class ReferenceLayer
    {
        public const int Index = 30;
        public const int Mask = 1 << Index;
        public static Vector3 World(V2 p, double z) => new Vector3((float)-p.Y, (float)z, (float)p.X);
        public static Vector3 World(double x, double y, double z) => new Vector3((float)-y, (float)z, (float)x);
    }

    /// <summary>
    /// Batched immediate-style drawing: call Clear, add primitives in course coordinates (odom metres), then Apply.
    /// One mesh per overlay; per-vertex colour, alpha supported. Heights follow the ramp via <see cref="Height"/>.
    /// </summary>
    public sealed class ReferenceOverlay : MonoBehaviour
    {
        private static Material shared;
        private readonly List<Vector3> vertices = new List<Vector3>();
        private readonly List<Color32> colors = new List<Color32>();
        private readonly List<Vector2> uvs = new List<Vector2>();
        private readonly List<int> triangles = new List<int>();
        private Mesh mesh;
        private MeshRenderer meshRenderer;
        private GameObject gridQuad;
        private Texture2D gridTexture;
        private Material gridMaterial;
        /// <summary>Ground height (m) under a course point; lines are drawn this much above it plus their own lift.</summary>
        public static Func<double, double, double> Height = (x, y) => 0;

        public static ReferenceOverlay Create(string name, Transform parent)
        {
            var go = new GameObject("Reference overlay: " + name) { layer = ReferenceLayer.Index };
            go.transform.SetParent(parent, false);
            var overlay = go.AddComponent<ReferenceOverlay>();
            overlay.mesh = new Mesh { name = "Reference overlay " + name, indexFormat = IndexFormat.UInt32 };
            overlay.mesh.MarkDynamic();
            go.AddComponent<MeshFilter>().sharedMesh = overlay.mesh;
            overlay.meshRenderer = go.AddComponent<MeshRenderer>();
            overlay.meshRenderer.sharedMaterial = SharedMaterial();
            overlay.meshRenderer.shadowCastingMode = ShadowCastingMode.Off; overlay.meshRenderer.receiveShadows = false;
            return overlay;
        }
        private static Material SharedMaterial()
        {
            if (shared != null) return shared;
            var shader = Shader.Find("IGVC/ReferenceOverlay");
            if (shader == null) throw new InvalidOperationException("IGVC/ReferenceOverlay shader missing from Resources; rebuild the player");
            shared = new Material(shader) { name = "Reference overlay", renderQueue = 3100 };
            return shared;
        }
        public bool Visible
        {
            get => gameObject.activeSelf;
            set => gameObject.SetActive(value);
        }
        public int VertexCount => vertices.Count;
        public void Clear() { vertices.Clear(); colors.Clear(); uvs.Clear(); triangles.Clear(); }
        public void Apply()
        {
            mesh.Clear();
            mesh.SetVertices(vertices); mesh.SetColors(colors); mesh.SetUVs(0, uvs); mesh.SetTriangles(triangles, 0, true);
        }
        private Vector3 At(V2 p, double lift) => ReferenceLayer.World(p, Height(p.X, p.Y) + lift);
        private void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Color32 ca, Color32 cb)
        {
            int n = vertices.Count;
            vertices.Add(a); vertices.Add(b); vertices.Add(c); vertices.Add(d);
            colors.Add(ca); colors.Add(cb); colors.Add(cb); colors.Add(ca);
            for (int i = 0; i < 4; i++) uvs.Add(Vector2.zero);
            triangles.Add(n); triangles.Add(n + 1); triangles.Add(n + 2); triangles.Add(n); triangles.Add(n + 2); triangles.Add(n + 3);
        }
        /// <summary>Flat ribbon on the ground, <paramref name="width"/> metres wide, lifted <paramref name="lift"/> metres.</summary>
        public void Line(V2 a, V2 b, Color color, double width = .05, double lift = .03) => Line(a, b, color, color, width, lift);
        public void Line(V2 a, V2 b, Color ca, Color cb, double width = .05, double lift = .03)
        {
            V2 n = (b - a).Normalized.Perp * (width / 2);
            if (n.SqrLength == 0) return;
            Quad(At(a - n, lift), At(b - n, lift), At(b + n, lift), At(a + n, lift), ca, cb);
        }
        public void Polyline(IList<V2> points, Color color, double width = .05, bool closed = false, double lift = .03)
        {
            if (points == null) return;
            for (int i = 0; i + 1 < points.Count; i++) Line(points[i], points[i + 1], color, width, lift);
            if (closed && points.Count > 2) Line(points[points.Count - 1], points[0], color, width, lift);
        }
        /// <summary>Polyline with one colour per vertex (e.g. a speed heat map).</summary>
        public void Polyline(IList<V2> points, IList<Color> perVertex, double width = .05, bool closed = false, double lift = .03)
        {
            if (points == null) return;
            int n = points.Count;
            for (int i = 0; i + 1 < n; i++) Line(points[i], points[i + 1], perVertex[i], perVertex[i + 1], width, lift);
            if (closed && n > 2) Line(points[n - 1], points[0], perVertex[n - 1], perVertex[0], width, lift);
        }
        public void Disc(V2 center, double radius, Color color, double lift = .03, int segments = 20)
        {
            int c = vertices.Count; Color32 col = color;
            vertices.Add(At(center, lift)); colors.Add(col); uvs.Add(Vector2.zero);
            for (int i = 0; i <= segments; i++)
            { vertices.Add(At(center + V2.FromAngle(2 * Math.PI * i / segments) * radius, lift)); colors.Add(col); uvs.Add(Vector2.zero); }
            for (int i = 0; i < segments; i++) { triangles.Add(c); triangles.Add(c + 2 + i); triangles.Add(c + 1 + i); }
        }
        public void Ring(V2 center, double radius, Color color, double width = .04, double lift = .03, int segments = 28)
        {
            for (int i = 0; i < segments; i++)
                Line(center + V2.FromAngle(2 * Math.PI * i / segments) * radius, center + V2.FromAngle(2 * Math.PI * (i + 1) / segments) * radius, color, width, lift);
        }
        /// <summary>Filled rectangle in a body frame: x in [-rear, front], y in [-half, half] about <paramref name="origin"/>.</summary>
        public void Box(V2 origin, double yaw, double front, double rear, double half, Color fill, double lift = .05)
        {
            V2 f = V2.FromAngle(yaw), l = f.Perp;
            Quad(At(origin - f * rear - l * half, lift), At(origin + f * front - l * half, lift), At(origin + f * front + l * half, lift), At(origin - f * rear + l * half, lift), fill, fill);
        }
        public void BoxOutline(V2 origin, double yaw, double front, double rear, double half, Color color, double width = .04, double lift = .06)
        {
            V2 f = V2.FromAngle(yaw), l = f.Perp;
            var c = new[] { origin - f * rear - l * half, origin + f * front - l * half, origin + f * front + l * half, origin - f * rear + l * half };
            Polyline(c, color, width, true, lift);
        }
        public void Capsule(Capsule c, Color color, double lift = .03)
        {
            Disc(c.A, c.R, color, lift); if (V2.Distance(c.A, c.B) < 1e-6) return;
            V2 n = (c.B - c.A).Normalized.Perp * c.R;
            Quad(At(c.A - n, lift), At(c.B - n, lift), At(c.B + n, lift), At(c.A + n, lift), color, color); Disc(c.B, c.R, color, lift);
        }

        /// <summary>
        /// Raster layer (one texel per grid cell) on a flat quad. Pixels are row-major from the (x0, y0) corner,
        /// +x then +y in course coordinates; call again with the same size to update cheaply.
        /// </summary>
        public void SetGrid(int width, int height, Color32[] pixels, double x0, double y0, double cell, double lift = .015)
        {
            if (gridQuad == null)
            {
                gridQuad = new GameObject("grid") { layer = ReferenceLayer.Index };
                gridQuad.transform.SetParent(transform, false);
                gridQuad.AddComponent<MeshFilter>().sharedMesh = new Mesh { name = "Reference grid quad" };
                var r = gridQuad.AddComponent<MeshRenderer>(); r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
                gridMaterial = new Material(SharedMaterial()) { name = "Reference grid", renderQueue = 3050 };
                r.sharedMaterial = gridMaterial;
            }
            if (gridTexture == null || gridTexture.width != width || gridTexture.height != height)
            {
                if (gridTexture != null) Destroy(gridTexture);
                gridTexture = new Texture2D(width, height, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp, name = "Reference grid" };
                gridMaterial.mainTexture = gridTexture;
            }
            gridTexture.SetPixels32(pixels); gridTexture.Apply(false);
            // Texture u runs along course +x (Unity +z), v along course +y (Unity -x).
            double x1 = x0 + width * cell, y1 = y0 + height * cell;
            var quad = gridQuad.GetComponent<MeshFilter>().sharedMesh; quad.Clear();
            quad.SetVertices(new List<Vector3> { ReferenceLayer.World(x0, y0, lift), ReferenceLayer.World(x1, y0, lift), ReferenceLayer.World(x1, y1, lift), ReferenceLayer.World(x0, y1, lift) });
            quad.SetUVs(0, new List<Vector2> { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) });
            quad.SetColors(new List<Color32> { Color.white, Color.white, Color.white, Color.white });
            quad.SetTriangles(new[] { 0, 1, 2, 0, 2, 3, 2, 1, 0, 3, 2, 0 }, 0);
            gridQuad.SetActive(true);
        }
        public void HideGrid() { if (gridQuad != null) gridQuad.SetActive(false); }

        private void OnDestroy()
        {
            if (mesh != null) Destroy(mesh);
            if (gridQuad != null) Destroy(gridQuad.GetComponent<MeshFilter>().sharedMesh);
            if (gridTexture != null) Destroy(gridTexture);
            if (gridMaterial != null) Destroy(gridMaterial);
        }
    }
}
