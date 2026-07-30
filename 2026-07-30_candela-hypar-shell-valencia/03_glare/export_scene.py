"""Export the Rhino model as a Radiance scene plus the sun/view definition.

Run inside Rhino 8 (IronPython 2.7). Writes into 03_glare/rad/.
Layers 01_Shell / 02_Glazing / 03_Terrace must be visible - Rhino's object
iterator skips hidden layers and would silently export nothing.
"""
import os, math
import Rhino
import Rhino.Geometry as rg

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rad") \
    if "__file__" in dir() else "."
MM = 1000.0                                   # model units -> metres
MATS = {"01_Shell": "shell_conc", "02_Glazing": "vision_glass",
        "03_Terrace": "terrace_conc"}
MONTH, DAY, HOUR = 6, 21, 17                  # low summer sun, worst case westward
EPW = os.path.join(os.path.expanduser("~"), "ladybug_tools", "resources", "weather",
                   "valencia_tmyx", "ESP_VC_Valencia.AP.082840_TMYx.2011-2025.epw")

rdoc = Rhino.RhinoDoc.ActiveDoc
for n in MATS:
    li = rdoc.Layers.FindByFullPath(n, -1)
    rdoc.Layers[li].IsVisible = True
    rdoc.Layers[li].CommitChanges()

mp = rg.MeshingParameters.QualityRenderMesh
mp.MaximumEdgeLength = 400.0                  # 0.4 m facets -> smooth soffit
mp.MinimumEdgeLength = 10.0
mp.GridAmplification = 2.0

lines, counts = ["# Candela hypar shell, metres", ""], {}
for o in list(rdoc.Objects):
    name = rdoc.Layers[o.Attributes.LayerIndex].Name
    if name not in MATS:
        continue
    geo = o.Geometry
    meshes = list(rg.Mesh.CreateFromBrep(geo, mp) or []) \
        if isinstance(geo, rg.Brep) else [geo]
    n = 0
    for mi, m in enumerate(meshes):
        m.Faces.ConvertQuadsToTriangles()
        for fi in range(m.Faces.Count):
            f = m.Faces[fi]
            pts = [m.Vertices[f.A], m.Vertices[f.B], m.Vertices[f.C]]
            lines.append("%s polygon %s.%d.%d\n0 0 9" % (MATS[name], MATS[name], mi, fi))
            lines.append("  " + "  ".join("%.5f %.5f %.5f"
                                          % (p.X / MM, p.Y / MM, p.Z / MM) for p in pts))
            lines.append("")
            n += 1
    counts[name] = counts.get(name, 0) + n
open(os.path.join(OUT, "geometry.rad"), "w").write("\n".join(lines))
print("triangles:", counts)

from ladybug.epw import EPW as EPWReader
from ladybug.sunpath import Sunpath
epw = EPWReader(EPW)
sun = Sunpath.from_location(epw.location).calculate_sun(MONTH, DAY, HOUR)
hoy = int(sun.datetime.hoy)
dni = epw.direct_normal_radiation.values[hoy]
dhi = epw.diffuse_horizontal_radiation.values[hoy]
open(os.path.join(OUT, "sun.txt"), "w").write(
    "%d %d %d %.4f %.4f %d %d\n" % (MONTH, DAY, HOUR, sun.altitude, sun.azimuth, dni, dhi))

az = math.radians(sun.azimuth)                # north = +Y, so azimuth is from +Y
dx, dy = math.sin(az), math.cos(az)
open(os.path.join(OUT, "view.txt"), "w").write(
    "%.4f %.4f %.4f %.5f %.5f 0\n" % (-6.0 * dx, -6.0 * dy, 1.60, dx, dy))
print("sun alt %.2f az %.2f  DNI %d  DHI %d" % (sun.altitude, sun.azimuth, dni, dhi))
