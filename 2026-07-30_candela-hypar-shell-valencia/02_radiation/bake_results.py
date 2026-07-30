"""Bake the Ladybug radiation results into Rhino layers, ready for capture.

Run inside Rhino 8 (IronPython 2.7) after build_radiation_graph.py has solved
with RUN = True.

The analysis mesh carries per-vertex colours, so it renders as a radiation map
in any shaded display mode. The legend arrives as one mesh plus Text3d entities.
"""
import Rhino
import Rhino.Geometry as rg
import Grasshopper as gh
import System.Drawing as sd

RAD_LAYER, LEG_LAYER = "05_Radiation", "06_Legend"

rdoc = Rhino.RhinoDoc.ActiveDoc
gdoc = gh.Instances.ActiveCanvas.Document
comp = [o for o in gdoc.Objects if o.NickName == "IncidentRadiation"][0]

def goos(nick):
    p = [q for q in comp.Params.Output if q.NickName == nick][0]
    return [g for br in p.VolatileData.Branches for g in br]

def layer(name, rgb):
    li = rdoc.Layers.FindByFullPath(name, -1)
    if li < 0:
        li = rdoc.Layers.Add(name, sd.Color.FromArgb(*rgb))
    for o in list(rdoc.Objects):
        if o.Attributes.LayerIndex == li:
            rdoc.Objects.Delete(o.Id, True)
    return li

li_rad = layer(RAD_LAYER, (255, 160, 0))
li_leg = layer(LEG_LAYER, (30, 30, 30))

att = Rhino.DocObjects.ObjectAttributes()
att.LayerIndex = li_rad
att.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
n_mesh = 0
for g in goos("mesh"):
    rdoc.Objects.AddMesh(g.Value, att)
    n_mesh += 1

att2 = Rhino.DocObjects.ObjectAttributes()
att2.LayerIndex = li_leg
n_leg = 0
for g in list(goos("legend")) + list(goos("title")):
    v = getattr(g, "Value", None)
    if isinstance(v, rg.Mesh):
        rdoc.Objects.AddMesh(v, att2); n_leg += 1
    elif isinstance(v, Rhino.Display.Text3d):
        rdoc.Objects.AddText(v, att2); n_leg += 1

comp.Hidden = True          # hide the live GH preview so only the bake shows
gdoc.NewSolution(False)
rdoc.Views.Redraw()
print("baked: %d analysis mesh, %d legend items" % (n_mesh, n_leg))
print("NOTE: this geometry is derived - it is intentionally not stored in the .3dm.")
