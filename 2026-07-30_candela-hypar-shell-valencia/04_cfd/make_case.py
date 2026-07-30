import os, math, shutil

SC = os.path.dirname(os.path.abspath(__file__))
CASE = os.path.join(SC, "case")
if os.path.isdir(CASE):
    shutil.rmtree(CASE)
for d in ("system", "constant", "0", "constant/triSurface"):
    os.makedirs(os.path.join(CASE, d.replace("system", "system")
                             .replace("constant", "constant")), exist_ok=True)
os.makedirs(os.path.join(CASE, "system"), exist_ok=True)
os.rename(os.path.join(CASE, "system"), os.path.join(CASE, "system"))
for stl in ("shell.stl", "glazing.stl"):
    shutil.copy(os.path.join(SC, "stl", stl),
                os.path.join(CASE, "constant/triSurface", stl))

HDR = """/*--------------------------------*- C++ -*----------------------------------*\\
| Candela hypar shell - natural ventilation, buoyantBoussinesqSimpleFoam       |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version 2.0; format ascii; class %s; %sobject %s;
}
"""
def hdr(cls, obj, loc=None):
    return HDR % (cls, ('location "%s"; ' % loc) if loc else "", obj)

def w(path, txt):
    p = os.path.join(CASE, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(txt)

# ---------------- domain: wind from the east, blowing toward -x ----------------
XMIN, XMAX = -140.0, 70.0
YMIN, YMAX = -70.0, 70.0
ZMIN, ZMAX = 0.0, 60.0
BASE = 3.5
nx = int(round((XMAX - XMIN) / BASE)); ny = int(round((YMAX - YMIN) / BASE))
nz = int(round((ZMAX - ZMIN) / BASE))

UREF, ZREF, Z0 = 4.4, 10.0, 0.5      # EPW: from E, 4.4 m/s mean over warm hours
T_AIR   = 301.45                     # 28.3 C outdoor air
T_GND   = 308.15                     # 35 C sun-heated terrace
T_SHELL = 306.15                     # 33 C concrete shell
T_GLASS = 304.15                     # 31 C glass

w("system/blockMeshDict", hdr("dictionary", "blockMeshDict", "system") + """
scale 1;
vertices
(
    (%g %g %g) (%g %g %g) (%g %g %g) (%g %g %g)
    (%g %g %g) (%g %g %g) (%g %g %g) (%g %g %g)
);
blocks ( hex (0 1 2 3 4 5 6 7) (%d %d %d) simpleGrading (1 1 1) );
edges ();
boundary
(
    inlet  { type patch; faces ( (1 2 6 5) ); }
    outlet { type patch; faces ( (0 4 7 3) ); }
    ground { type wall;  faces ( (0 3 2 1) ); }
    top    { type patch; faces ( (4 5 6 7) ); }
    sides  { type patch; faces ( (0 1 5 4) (3 7 6 2) ); }
);
mergePatchPairs ();
""" % (XMIN, YMIN, ZMIN, XMAX, YMIN, ZMIN, XMAX, YMAX, ZMIN, XMIN, YMAX, ZMIN,
       XMIN, YMIN, ZMAX, XMAX, YMIN, ZMAX, XMAX, YMAX, ZMAX, XMIN, YMAX, ZMAX,
       nx, ny, nz))

w("system/snappyHexMeshDict", hdr("dictionary", "snappyHexMeshDict", "system") + """
castellatedMesh true;
snap            true;
addLayers       false;

geometry
{
    shell.stl   { type triSurfaceMesh; name shell; }
    glazing.stl { type triSurfaceMesh; name glazing; }
    nearBox     { type searchableBox; min (-34 -34 0); max (34 34 22); }
}

castellatedMeshControls
{
    maxLocalCells   4000000;
    maxGlobalCells  8000000;
    minRefinementCells 0;
    nCellsBetweenLevels 2;
    maxLoadUnbalance 0.1;
    resolveFeatureAngle 40;
    allowFreeStandingZoneFaces true;
    features ();
    refinementSurfaces
    {
        shell   { level (2 3); faceZone shellFaces;   faceType baffle; }
        glazing { level (3 3); faceZone glazingFaces; faceType baffle; }
    }
    refinementRegions
    {
        nearBox { mode inside; levels ((1e15 2)); }
    }
    locationInMesh (60.0 55.0 30.0);
}

snapControls
{
    nSmoothPatch 3; tolerance 2.0; nSolveIter 40; nRelaxIter 6;
    nFeatureSnapIter 10; implicitFeatureSnap false;
    explicitFeatureSnap true; multiRegionFeatureSnap false;
}

addLayersControls
{
    relativeSizes true; layers {}; expansionRatio 1.2;
    finalLayerThickness 0.4; minThickness 0.1; nGrow 0;
    featureAngle 60; nRelaxIter 5; nSmoothSurfaceNormals 1;
    nSmoothNormals 3; nSmoothThickness 10; maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90; nBufferCellsNoExtrude 0;
    nLayerIter 50;
}

meshQualityControls
{
    maxNonOrtho 68; maxBoundarySkewness 20; maxInternalSkewness 4;
    maxConcave 80; minVol 1e-13; minTetQuality -1; minArea -1;
    minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.02;
    minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4;
    errorReduction 0.75;
}
mergeTolerance 1e-6;
""")

w("system/controlDict", hdr("dictionary", "controlDict", "system") + """
application     buoyantBoussinesqSimpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         900;
deltaT          1;
writeControl    timeStep;
writeInterval   300;
purgeWrite      2;
writeFormat     ascii;
writePrecision  7;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
""")

w("system/fvSchemes", hdr("dictionary", "fvSchemes", "system") + """
ddtSchemes      { default steadyState; }
gradSchemes     { default cellLimited Gauss linear 1; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,T)      bounded Gauss limitedLinear 1;
    div(phi,k)      bounded Gauss limitedLinear 1;
    div(phi,epsilon) bounded Gauss limitedLinear 1;
    div(phi,R)      bounded Gauss limitedLinear 1;
    div(R)          Gauss linear;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
wallDist        { method meshWave; }
""")

w("system/fvSolution", hdr("dictionary", "fvSolution", "system") + """
solvers
{
    p_rgh
    {
        solver GAMG; tolerance 1e-7; relTol 0.01;
        smoother GaussSeidel;
    }
    "(U|T|k|epsilon)"
    {
        solver PBiCGStab; preconditioner DILU;
        tolerance 1e-8; relTol 0.1;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    pRefCell 0;
    pRefValue 0;
    residualControl { p_rgh 1e-3; U 1e-4; T 1e-4; "(k|epsilon)" 1e-3; }
}
relaxationFactors
{
    fields  { p_rgh 0.3; }
    equations { U 0.5; T 0.5; "(k|epsilon)" 0.5; }
}
""")

w("constant/g", hdr("uniformDimensionedVectorField", "g", "constant") + """
dimensions [0 1 -2 0 0 0 0];
value (0 0 -9.81);
""")

w("constant/transportProperties", hdr("dictionary", "transportProperties", "constant") + """
nu   [0 2 -1 0 0 0 0] 1.5e-05;
beta [0 0 0 -1 0 0 0] 3.31e-03;
TRef [0 0 0 1 0 0 0] %g;
Pr   [0 0 0 0 0 0 0] 0.71;
Prt  [0 0 0 0 0 0 0] 0.85;
""" % T_AIR)

w("constant/momentumTransport", hdr("dictionary", "momentumTransport", "constant") + """
simulationType RAS;
RAS { model kEpsilon; turbulence on; printCoeffs on; }
""")
w("constant/turbulenceProperties", hdr("dictionary", "turbulenceProperties", "constant") + """
simulationType RAS;
RAS { RASModel kEpsilon; turbulence on; printCoeffs on; }
""")

WALLS = ["ground", "shell", "glazing"]
def wall_block(field, body):
    return "\n".join("    %s\n    {\n%s\n    }\n" % (p, body) for p in WALLS)

w("0/U", hdr("volVectorField", "U", "0") + """
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    inlet
    {
        type            atmBoundaryLayerInletVelocity;
        flowDir         (-1 0 0);
        zDir            (0 0 1);
        Uref            %g;
        Zref            %g;
        z0              uniform %g;
        d               uniform 0;
        value           uniform (0 0 0);
    }
    outlet  { type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0); }
    top     { type slip; }
    sides   { type slip; }
%s
}
""" % (UREF, ZREF, Z0, wall_block("U", "        type            noSlip;")))

w("0/p_rgh", hdr("volScalarField", "p_rgh", "0") + """
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet   { type fixedFluxPressure; value uniform 0; }
    outlet  { type fixedValue; value uniform 0; }
    top     { type slip; }
    sides   { type slip; }
%s
}
""" % wall_block("p_rgh", "        type            fixedFluxPressure;\n        value           uniform 0;"))

w("0/T", hdr("volScalarField", "T", "0") + """
dimensions [0 0 0 1 0 0 0];
internalField uniform %g;
boundaryField
{
    inlet   { type fixedValue; value uniform %g; }
    outlet  { type inletOutlet; inletValue uniform %g; value uniform %g; }
    top     { type slip; }
    sides   { type slip; }
    ground  { type fixedValue; value uniform %g; }
    shell   { type fixedValue; value uniform %g; }
    glazing { type fixedValue; value uniform %g; }
}
""" % (T_AIR, T_AIR, T_AIR, T_AIR, T_GND, T_SHELL, T_GLASS))

w("0/k", hdr("volScalarField", "k", "0") + """
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0.5;
boundaryField
{
    inlet
    {
        type            atmBoundaryLayerInletK;
        flowDir         (-1 0 0);
        zDir            (0 0 1);
        Uref            %g;
        Zref            %g;
        z0              uniform %g;
        d               uniform 0;
        value           uniform 0.5;
    }
    outlet  { type inletOutlet; inletValue uniform 0.5; value uniform 0.5; }
    top     { type slip; }
    sides   { type slip; }
%s
}
""" % (UREF, ZREF, Z0,
       wall_block("k", "        type            kqRWallFunction;\n        value           uniform 0.5;")))

w("0/epsilon", hdr("volScalarField", "epsilon", "0") + """
dimensions [0 2 -3 0 0 0 0];
internalField uniform 0.1;
boundaryField
{
    inlet
    {
        type            atmBoundaryLayerInletEpsilon;
        flowDir         (-1 0 0);
        zDir            (0 0 1);
        Uref            %g;
        Zref            %g;
        z0              uniform %g;
        d               uniform 0;
        value           uniform 0.1;
    }
    outlet  { type inletOutlet; inletValue uniform 0.1; value uniform 0.1; }
    top     { type slip; }
    sides   { type slip; }
%s
}
""" % (UREF, ZREF, Z0,
       wall_block("epsilon", "        type            epsilonWallFunction;\n        value           uniform 0.1;")))

w("0/nut", hdr("volScalarField", "nut", "0") + """
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet   { type calculated; value uniform 0; }
    outlet  { type calculated; value uniform 0; }
    top     { type slip; }
    sides   { type slip; }
%s
}
""" % wall_block("nut", "        type            nutkAtmRoughWallFunction;\n        z0              uniform 0.5;\n        value           uniform 0;"))

w("0/alphat", hdr("volScalarField", "alphat", "0") + """
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet   { type calculated; value uniform 0; }
    outlet  { type calculated; value uniform 0; }
    top     { type slip; }
    sides   { type slip; }
%s
}
""" % wall_block("alphat", "        type            compressible::alphatWallFunction;\n        Prt             0.85;\n        value           uniform 0;"))

# ---------------- sampling: horizontal plane at 1.5 m + E-W vertical section ---
def probe_points():
    pts = []
    x = -24.0
    while x <= 24.0001:
        y = -24.0
        while y <= 24.0001:
            pts.append((x, y, 1.5))
            y += 0.6
        x += 0.6
    n_plane = len(pts)
    x = -26.0
    while x <= 26.0001:
        z = 0.2
        while z <= 14.0001:
            pts.append((x, 0.0, z))
            z += 0.35
        x += 0.6
    return pts, n_plane

pts, n_plane = probe_points()
w("system/sampleDict", hdr("dictionary", "sampleDict", "system") + """
type            probes;
libs            ("libsampling.so");
fields          (U T p_rgh);
probeLocations
(
%s
);
""" % "\n".join("    (%g %g %g)" % p for p in pts))
with open(os.path.join(SC, "probe_meta.txt"), "w") as fh:
    fh.write("%d %d\n" % (len(pts), n_plane))

print("case written: %s" % CASE)
print("  blockMesh cells: %d x %d x %d = %d" % (nx, ny, nz, nx * ny * nz))
print("  domain x %g..%g  y %g..%g  z %g..%g" % (XMIN, XMAX, YMIN, YMAX, ZMIN, ZMAX))
print("  probes: %d total (%d on the z=1.5 m plane, %d on the y=0 section)"
      % (len(pts), n_plane, len(pts) - n_plane))
