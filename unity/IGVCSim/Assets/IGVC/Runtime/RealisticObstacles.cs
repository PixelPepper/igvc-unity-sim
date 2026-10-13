using System.Collections.Generic;
using UnityEngine;

namespace IGVC
{
    // Detailed traffic-drum visual mesh (adapted from the parked sim-realism RealisticObstacles; T-0090).
    // Submesh 0 = ribbed tapered body, 1 = two reflective bands, 2 = rubber base ring. Visual only: callers
    // keep the original drum collider unchanged, and every surface stays inside a cylinder of the given
    // diameter and height so depth/lidar envelopes do not grow. Bands sit at 0.34 h and 0.68 h, 9 cm tall.
    public static class RealisticObstacles
    {
        private const int Segments = 40;

        public static Mesh DrumMesh(string name, float diameter, float height)
        {
            float h = height, R = diameter / 2;
            var profile = new List<Vector2>();   // (radius, height)
            void Add(float r, float y) => profile.Add(new Vector2(r * R, y));
            Add(0, 0); Add(.97f, 0); Add(1f, .012f); Add(1f, .055f); Add(.95f, .075f); Add(.9f, .08f);
            float bottom = .08f, top = .95f * h;
            float Body(float y) => .9f - .11f * (y - bottom) / (top - bottom);
            var ridges = new List<float> { .2f * h, .5f * h, .84f * h };
            var cuts = new List<float> { bottom };
            foreach (var y in ridges) cuts.AddRange(new[] { y - .012f, y - .006f, y + .006f, y + .012f });
            foreach (var c in new[] { .34f * h, .68f * h }) cuts.AddRange(new[] { c - .045f, c + .045f });
            cuts.Add(top); cuts.Sort();
            foreach (var y in cuts)
            {
                bool lip = ridges.Exists(r => Mathf.Abs(Mathf.Abs(y - r) - .006f) < 1e-4f);
                Add(Body(y) + (lip ? .018f : 0), y);
            }
            Add(.72f, .975f * h); Add(.5f, .993f * h); Add(.25f, h); Add(0, h);

            var vertices = new List<Vector3>(); var normals = new List<Vector3>(); var uvs = new List<Vector2>();
            var tire = new List<int>(); var shell = new List<int>(); var bands = new List<int>();
            for (int i = 0; i + 1 < profile.Count; i++)
            {
                Vector2 a = profile[i], b = profile[i + 1];
                if ((a - b).sqrMagnitude < 1e-10f) continue;
                var along = (b - a).normalized; var outward = new Vector2(along.y, -along.x);
                float mid = (a.y + b.y) / 2;
                var target = mid <= bottom ? tire
                    : Mathf.Abs(mid - .34f * h) < .045f || Mathf.Abs(mid - .68f * h) < .045f ? bands : shell;
                for (int s = 0; s < Segments; s++)
                {
                    float t0 = s * 2 * Mathf.PI / Segments, t1 = (s + 1) * 2 * Mathf.PI / Segments;
                    int n = vertices.Count;
                    foreach (var (p, t) in new[] { (a, t0), (a, t1), (b, t1), (b, t0) })
                    {
                        // Centred on the cylinder primitive's pivot (half height), so it replaces it in place.
                        vertices.Add(new Vector3(p.x * Mathf.Cos(t), p.y - h / 2, p.x * Mathf.Sin(t)));
                        normals.Add(new Vector3(outward.x * Mathf.Cos(t), outward.y, outward.x * Mathf.Sin(t)).normalized);
                        uvs.Add(new Vector2(t * R, p.y));
                    }
                    target.AddRange(new[] { n, n + 2, n + 1, n, n + 3, n + 2 });
                }
            }
            var mesh = new Mesh { name = name };
            mesh.SetVertices(vertices); mesh.SetNormals(normals); mesh.SetUVs(0, uvs);
            mesh.subMeshCount = 3;
            mesh.SetTriangles(shell, 0); mesh.SetTriangles(bands, 1); mesh.SetTriangles(tire, 2);
            mesh.RecalculateTangents(); mesh.RecalculateBounds();
            return mesh;
        }
    }
}
