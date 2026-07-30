"""Add the Ladybug annual-radiation chain to the open Grasshopper document.

Run inside Rhino 8 (IronPython 2.7) after 01_model/src/build_gh_definition.py.

The Ladybug user objects are not registered in the ribbon until Rhino restarts,
so they are instantiated straight from their .ghuser files instead.
"""
import os
import System.Drawing as sd
from System import Decimal
import Grasshopper as gh
from Grasshopper.Kernel.Special import GH_Panel, GH_BooleanToggle, GH_NumberSlider

UO = os.path.join(os.path.expanduser("~"),
                  "Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins",
                  "Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)",
                  "UserObjects", "ladybug_tools")
EPW = os.path.join(os.path.expanduser("~"), "ladybug_tools", "resources", "weather",
                   "valencia_tmyx", "ESP_VC_Valencia.AP.082840_TMYx.2011-2025.epw")
GRID_MM = 1000.0          # model units are millimetres

gdoc = gh.Instances.ActiveCanvas.Document

def add_lb(name, x, y):
    o = gh.Kernel.GH_UserObject(os.path.join(UO, name + ".ghuser")).InstantiateObject()
    o.CreateAttributes()
    o.Attributes.Pivot = sd.PointF(x, y)
    o.NickName = name.replace("LB ", "").replace(" ", "")
    gdoc.AddObject(o, False)
    return o

def pin(o, n):  return [p for p in o.Params.Input if p.NickName == n][0]
def pout(o, n): return [p for p in o.Params.Output if p.NickName == n][0]

panel = GH_Panel(); panel.CreateAttributes()
panel.Attributes.Pivot = sd.PointF(700, 40); panel.NickName = "epw_path"
panel.UserText = EPW; panel.Properties.Multiline = False
gdoc.AddObject(panel, False)

grid = GH_NumberSlider(); grid.CreateAttributes()
grid.Attributes.Pivot = sd.PointF(700, 300); grid.NickName = "grid_size_mm"
grid.Attributes.ExpireLayout(); grid.Attributes.PerformLayout()
grid.Slider.Minimum = Decimal(300); grid.Slider.Maximum = Decimal(3000)
grid.Slider.DecimalPlaces = 0; grid.Slider.Value = Decimal(GRID_MM)
gdoc.AddObject(grid, False)

run = GH_BooleanToggle(); run.CreateAttributes()
run.Attributes.Pivot = sd.PointF(700, 360); run.NickName = "RUN"; run.Value = False
gdoc.AddObject(run, False)

epw_c = add_lb("LB Import EPW", 900, 40)
sky_c = add_lb("LB Cumulative Sky Matrix", 1120, 40)
rad_c = add_lb("LB Incident Radiation", 1360, 40)

pin(epw_c, "_epw_file").AddSource(panel)
pin(sky_c, "_location").AddSource(pout(epw_c, "location"))
pin(sky_c, "_direct_rad").AddSource(pout(epw_c, "direct_normal_rad"))
pin(sky_c, "_diffuse_rad").AddSource(pout(epw_c, "diffuse_horizontal_rad"))
pin(rad_c, "_sky_mtx").AddSource(pout(sky_c, "sky_mtx"))
pin(rad_c, "_grid_size").AddSource(grid)
pin(rad_c, "_run").AddSource(run)
shell = [o for o in gdoc.Objects if o.NickName == "Candela hypar vault"][0]
pin(rad_c, "_geometry").AddSource(pout(shell, "a"))

# gendaymtx is launched as a subprocess and needs RAYPATH; launchctl only reaches
# apps started afterwards, so set it in-process too
os.environ["RAYPATH"] = os.path.join(os.path.expanduser("~"), "ladybug_tools",
                                     "radiance", "lib")
run.Value = True
gdoc.NewSolution(True)
print("wired. flip RUN and re-solve if results are empty.")
