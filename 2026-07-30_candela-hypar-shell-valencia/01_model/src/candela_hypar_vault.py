"""Candela hypar flower - Valencia "Restaurante Submarino" (2002) proportions.

n hyperbolic-paraboloid lobes share one central crown. Each lobe carries its
two adjacent groins as straight generators, so a groin runs dead straight from
the crown down to its ground support. A hypar's two generator families need not
be perpendicular, so the same construction works for any lobe count: the plan
sector angle is 360/n and the generators run along its two edges.

Only the trim outline departs from Los Manantiales: instead of a straight-in-
plan cut, each lobe is trimmed by a rim that leaves the notch tangent to the
groin and swells to a rounded tip. That keeps the free edge on the ground at
the notches while giving the broad curled petals of the Valencia shell.

    x = crown height (m)      w = glazing setback (fraction)
    y = lobe tip height (m)   v = lobe tip radius (m)
    z = support radius (m)    u = lobe bluntness (>= 2 keeps the edge above 0)
                              n = lobe count

    a = shell    b = perimeter glazing    c = terrace slab
"""
import math
import Rhino.Geometry as rg

MM  = 1000.0
TOL = 10.0
N   = 60                      # samples along one lobe rim

R_TIP   = (20.00 if v is None else float(v)) * MM
h_crown = ( 8.00 if x is None else float(x)) * MM
h_tip   = (15.00 if y is None else float(y)) * MM
R_SUP   = (11.00 if z is None else float(z)) * MM
F_GLASS = 0.85 if w is None else float(w)
Q_BLUNT = 2.20 if u is None else float(u)
NL      = 8 if n is None else max(3, int(round(float(n))))

beta = 2.0 * math.pi / NL                 # plan sector of one lobe
th0  = 0.5 * math.pi - 0.5 * beta         # first groin; lobe axis points +Y
px, py = math.cos(th0), math.sin(th0)
qx, qy = math.cos(th0 + beta), math.sin(th0 + beta)
det = px * qy - py * qx                   # = sin(beta)

tau = R_TIP / (2.0 * math.cos(0.5 * beta))   # tip, measured along a generator
d   = R_SUP                                  # support, along a generator
gam = (h_tip - h_crown + 2.0 * h_crown * tau / d) / (tau * tau)

def st_of(ax, ay):
    return ((ax * qy - ay * qx) / det, (px * ay - py * ax) / det)

def zst(s, t):
    return h_crown - h_crown * (s + t) / d + gam * s * t

def pst(s, t):
    return rg.Point3d(s * px + t * qx, s * py + t * qy, zst(s, t))

def zof(ax, ay):
    return zst(*st_of(ax, ay))

def rim(alpha):
    return R_SUP + (R_TIP - R_SUP) * math.sin(math.pi * alpha) ** Q_BLUNT

def rim_pt(alpha, scale, lift):
    th = th0 + beta * alpha
    r = rim(alpha) * scale
    ax, ay = r * math.cos(th), r * math.sin(th)
    return rg.Point3d(ax, ay, zof(ax, ay) if lift else 0.0)

# --- untrimmed hypar, exactly bilinear over an (s,t) square that covers the lobe
smax = 0.0
for i in range(N + 1):
    q = rim_pt(i / float(N), 1.0, False)
    ss, tt = st_of(q.X, q.Y)
    smax = max(smax, ss, tt)
S = smax * 1.35
hypar = rg.NurbsSurface.CreateFromCorners(pst(0.0, 0.0), pst(S, 0.0),
                                          pst(S, S), pst(0.0, S))

# --- lobe footprint: crown, the rim from notch to notch, back to crown
plan = [rg.Point3d(0.0, 0.0, 0.0)]
plan += [rim_pt(i / float(N), 1.0, False) for i in range(N + 1)]
plan.append(rg.Point3d(0.0, 0.0, 0.0))
foot = rg.PolylineCurve(plan)

lo, hi = -0.7 * R_TIP, 1.7 * R_TIP
base = foot.DuplicateCurve()
base.Translate(rg.Vector3d(0.0, 0.0, lo))
prism = rg.Brep.CreateFromSurface(
    rg.Surface.CreateExtrusion(base, rg.Vector3d(0.0, 0.0, hi - lo)))
prism = prism.CapPlanarHoles(TOL) or prism

lobe, how = None, "split"
for pc in (rg.Brep.CreateFromSurface(hypar).Split(prism, TOL) or []):
    amp = rg.AreaMassProperties.Compute(pc)
    if amp is None:
        continue
    c = amp.Centroid
    if foot.Contains(rg.Point3d(c.X, c.Y, 0.0), rg.Plane.WorldXY,
                     TOL) == rg.PointContainment.Inside:
        lobe = pc
        break

if lobe is None:
    how = "mesh"
    NR = 22
    lobe = rg.Mesh()
    for i in range(N + 1):
        al = i / float(N)
        th = th0 + beta * al
        rr_ = rim(al)
        for j in range(NR + 1):
            rho = j / float(NR)
            ax, ay = rho * rr_ * math.cos(th), rho * rr_ * math.sin(th)
            lobe.Vertices.Add(rg.Point3d(ax, ay, zof(ax, ay)))
    for i in range(N):
        for j in range(NR):
            aa = i * (NR + 1) + j
            bb = aa + NR + 1
            lobe.Faces.AddFace(aa, aa + 1, bb + 1, bb)
    lobe.Normals.ComputeNormals()
    lobe.Compact()

def glass_wall(scale):
    out = rg.Brep()
    prev_b = prev_t = None
    for i in range(N + 1):
        t_ = rim_pt(i / float(N), scale, True)
        b_ = rg.Point3d(t_.X, t_.Y, 0.0)
        if prev_b is not None:
            quad = rg.Brep.CreateFromCornerPoints(prev_b, b_, t_, prev_t, TOL)
            if quad:
                out.Append(quad)
        prev_b, prev_t = b_, t_
    return out

ring = []
for lb in range(NL):
    for i in range(N):
        al = i / float(N)
        th = th0 + beta * (lb + al)
        r = rim(al)
        ring.append(rg.Point3d(r * math.cos(th), r * math.sin(th), 0.0))
ring.append(ring[0])
slab = rg.Brep.CreatePlanarBreps([rg.PolylineCurve(ring)], TOL)

def merge(items):
    out = rg.Brep()
    for it in items:
        out.Append(it)
    return out

shell_parts, glass_parts = [], []
for i in range(NL):
    xf = rg.Transform.Rotation(beta * i, rg.Vector3d.ZAxis, rg.Point3d.Origin)
    sp = lobe.Duplicate()
    sp.Transform(xf)
    shell_parts.append(sp)
    gw = glass_wall(F_GLASS)
    gw.Transform(xf)
    glass_parts.append(gw)

if how == "split":
    a = merge(shell_parts)
else:
    a = rg.Mesh()
    for m in shell_parts:
        a.Append(m)
b = merge(glass_parts)
c = merge(list(slab) if slab else [])

edge_z = [rim_pt(i / float(N), 1.0, True).Z for i in range(N + 1)]
print("%d lobes, sector %.1f deg, shell by %s"
      % (NL, math.degrees(beta), how))
print("free edge z: min %+.2f m  max %+.2f m   (min must not go below 0)"
      % (min(edge_z) / MM, max(edge_z) / MM))
print("groin lands at z = %.3f mm  |  crown %.1f m  tip %.1f m  blunt %.2f"
      % (pst(d, 0.0).Z, h_crown / MM, h_tip / MM, Q_BLUNT))
print("plan: tip span %.1f m  notch ring dia %.1f m  adjacent notches %.1f m"
      % (2 * R_TIP / MM, 2 * R_SUP / MM,
         2 * R_SUP * math.sin(0.5 * beta) / MM))
print("glass %.1f m at lobe centre, %.1f m at notch"
      % (rim_pt(0.5, F_GLASS, True).Z / MM, rim_pt(0.0, F_GLASS, True).Z / MM))
