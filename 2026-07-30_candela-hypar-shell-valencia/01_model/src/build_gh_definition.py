"""Rebuild the parametric Grasshopper definition from scratch.

Run inside Rhino 8 (IronPython 2.7) - Rhino's Python editor, or the rhinomcp
`execute_rhinoscript_python_code` tool.

The MCP/Grasshopper API cannot set a script component's body through the normal
component-creation path (a `content` field is silently ignored), so the source is
installed with Python3Component.SetSource(). Extra script inputs/outputs are
added through the IGH_VariableParameterComponent interface.
"""
import os
import System
import System.Drawing as sd
from System import Decimal
import Grasshopper as gh
from Grasshopper.Kernel import GH_ParameterSide
from Grasshopper.Kernel.Special import GH_NumberSlider

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "."
SRC = os.path.join(HERE, "candela_hypar_vault.py")
PY3_GUID = "719467e6-7cf5-4848-99b0-c5dd57e5442c"      # Python 3 Script

SLIDERS = [                       # nickname, value, min, max, decimals, script input
    ("h_crown_m",      6.50,  2.0, 16.0, 2, "x"),
    ("h_tip_m",       11.50,  2.0, 25.0, 2, "y"),
    ("R_support_m",   16.00,  3.0, 20.0, 2, "z"),
    ("glass_setback",  0.62,  0.4, 0.98, 2, "w"),
    ("R_tip_m",       20.00, 10.0, 32.0, 2, "v"),
    ("lobe_bluntness", 1.20,  0.4,  5.0, 2, "u"),
    ("lobe_count",     8.00,  3.0, 12.0, 0, "n"),
]

if gh.Instances.ActiveCanvas.Document is None:
    gh.Instances.DocumentServer.AddDocument(gh.Kernel.GH_Document(), True)
gdoc = gh.Instances.ActiveCanvas.Document

comp = gh.Instances.ComponentServer.EmitObject(System.Guid(PY3_GUID))
comp.CreateAttributes()
comp.Attributes.Pivot = sd.PointF(320, 40)
comp.NickName = "Candela hypar vault"
gdoc.AddObject(comp, False)

# the component ships with inputs x,y and outputs out,a - add the rest
for idx, nick in ((2, "z"), (3, "w"), (4, "v"), (5, "u"), (6, "n")):
    if comp.CanInsertParameter(GH_ParameterSide.Input, idx):
        p = comp.CreateParameter(GH_ParameterSide.Input, idx)
        p.NickName = p.Name = nick
        comp.Params.RegisterInputParam(p, idx)
for idx, nick in ((2, "b"), (3, "c")):
    if comp.CanInsertParameter(GH_ParameterSide.Output, idx):
        p = comp.CreateParameter(GH_ParameterSide.Output, idx)
        p.NickName = p.Name = nick
        comp.Params.RegisterOutputParam(p, idx)
comp.Params.OnParametersChanged()
comp.VariableParameterMaintenance()

comp.SetSource(open(SRC).read())

by_nick = dict((p.NickName, p) for p in comp.Params.Input)
for i, (nick, val, lo, hi, dec, tgt) in enumerate(SLIDERS):
    s = GH_NumberSlider()
    s.CreateAttributes()
    s.Attributes.Pivot = sd.PointF(60, 40 + 34 * i)
    # API-made sliders keep a zero-width grip until laid out, and their value
    # drifts on the next redraw unless the layout is forced first
    s.Attributes.ExpireLayout()
    s.Attributes.PerformLayout()
    s.Slider.Minimum = Decimal(lo)
    s.Slider.Maximum = Decimal(hi)
    s.Slider.DecimalPlaces = dec
    s.Slider.Value = Decimal(val)
    s.NickName = nick
    gdoc.AddObject(s, False)
    by_nick[tgt].AddSource(s)

comp.ExpireSolution(True)
gdoc.NewSolution(True)
print("built. runtime report:")
for br in comp.Params.Output[0].VolatileData.Branches:
    for it in br:
        print("   ", it)
