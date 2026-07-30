"""Export the shell and glazing as STL for snappyHexMesh, with two bays opened.

Run inside Rhino 8 (IronPython 2.7). Writes into 04_cfd/stl/.

Lobe i occupies the 360/n degree plan sector centred on azimuth (360 - 45*i) %% 360
(for n = 8), so a glazing triangle is dropped simply by classifying its centroid.
Removing bays 6 and 2 opens the east (windward) and west (leeward) faces.
"""
import os, math
import Rhino
import Rhino.Geometry as rg

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl") \
    if "__file__" in dir() else "."
MM = 1000.0
NL = 8
OPEN_LOBES = (6, 2)

rdoc = Rhino.RhinoDoc.ActiveDoc
for n in ("01_Shell", "02_Glazing"):
    li = rdoc.Layers.FindByFullPath(n, -1)
    rdoc.Layers[li].IsVisible = True
    rdoc.Layers[li].CommitChanges()

def lobe_of(px, py):
    az = math.degrees(math.atan2(px, py)) % 360.0
    return int(round(((360.0 - az) % 360.0) / (360.0 / NL))) % NL

mp = rg.MeshingParameters.QualityRenderMesh
mp.MaximumEdgeLength = 600.0
mp.MinimumEdgeLength = 20.0

def tris(layer):
    li = rdoc.Layers.FindByFullPath(layer, -1)
    out = []
    for o in list(rdoc.Objects):
        if o.Attributes.LayerIndex != li:
            continue
        geo = o.Geometry
        for m in (list(rg.Mesh.CreateFromBrep(geo, mp) or [])
                  if isinstance(geo, rg.Brep) else [geo]):
            m.Faces.ConvertQuadsToTriangles()
            for fi in range(m.Faces.Count):
                f = m.Faces[fi]
                out.append([m.Vertices[f.A], m.Vertices[f.B], m.Vertices[f.C]])
    return out

def write_stl(path, name, tri):
    with open(path, "w") as fh:
        fh.write("solid %s\n" % name)
        for t in tri:
            a, b, c = [rg.Point3d(p.X / MM, p.Y / MM, p.Z / MM) for p in t]
            nv = rg.Vector3d.CrossProduct(b - a, c - a)
            if nv.Length > 0:
                nv.Unitize()
            fh.write("  facet normal %.6f %.6f %.6f\n    outer loop\n" % (nv.X, nv.Y, nv.Z))
            for p in (a, b, c):
                fh.write("      vertex %.5f %.5f %.5f\n" % (p.X, p.Y, p.Z))
            fh.write("    endloop\n  endfacet\n")
        fh.write("endsolid %s\n" % name)

shell = tris("01_Shell")
write_stl(os.path.join(OUT, "shell.stl"), "shell", shell)
glass = tris("02_Glazing")
kept = [t for t in glass
        if lobe_of(sum(p.X for p in t) / 3.0, sum(p.Y for p in t) / 3.0) not in OPEN_LOBES]
write_stl(os.path.join(OUT, "glazing.stl"), "glazing", kept)
print("shell %d tris, glazing %d of %d kept (%d%% removed = %d of %d bays)"
      % (len(shell), len(kept), len(glass),
         100 * (len(glass) - len(kept)) / len(glass), len(OPEN_LOBES), NL))
