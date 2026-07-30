import os, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.dirname(HERE)                    # 04_cfd/
PROJ = os.path.dirname(SC)
OUT = os.path.join(PROJ, "05_images", "cfd")
DATA = os.path.join(SC, "results")            # U and T probe dumps

def last_line(p):
    l = None
    for line in open(p):
        if not line.startswith("#"):
            l = line
    return l

U = np.array([[float(v) for v in c.split(")")[0].split()]
              for c in last_line(os.path.join(DATA, "U")).split("(")[1:]])
T = np.array([float(x) for x in last_line(os.path.join(DATA, "T")).split()[1:]]) - 273.15
UMAG = np.linalg.norm(U, axis=1)
planes = json.load(open(os.path.join(HERE, "planes.json")))["planes"]

def load_stl(p):
    tris, cur = [], []
    for line in open(p):
        s = line.strip()
        if s.startswith("vertex"):
            cur.append([float(v) for v in s.split()[1:4]])
            if len(cur) == 3:
                tris.append(cur); cur = []
    return np.array(tris)
STL = {n: load_stl(os.path.join(SC, "stl", n + ".stl"))
       for n in ("shell", "glazing")}

def section_segments(tris, fval, to_uv):
    segs = []
    f = fval(tris.reshape(-1, 3)).reshape(-1, 3)
    for i in range(len(tris)):
        d, p = f[i], tris[i]
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (d[a] > 0) != (d[b] > 0):
                t = d[a] / (d[a] - d[b])
                pts.append(p[a] + t * (p[b] - p[a]))
        if len(pts) == 2:
            segs.append((to_uv(pts[0]), to_uv(pts[1])))
    return segs

SPEC = {"ew":   (lambda P: P[:, 1], lambda p: (p[0], p[2])),
        "ns":   (lambda P: P[:, 0], lambda p: (p[1], p[2])),
        "diag": (lambda P: P[:, 1] - P[:, 0], lambda p: (p[0] * math.sqrt(2.0), p[2]))}

# ---------------- ventilation rate across the x = 0 interior plane ----------
R_TIP, R_SUP, h_crown, h_tip = 20.0, 16.0, 6.5, 11.5
F_GLASS, Q_BLUNT, NL = 0.62, 1.2, 8
beta = 2.0 * math.pi / NL
th0 = 0.5 * math.pi - 0.5 * beta
px, py = math.cos(th0), math.sin(th0)
qx, qy = math.cos(th0 + beta), math.sin(th0 + beta)
det = px * qy - py * qx
tau = R_TIP / (2.0 * math.cos(0.5 * beta))
gam = (h_tip - h_crown + 2.0 * h_crown * tau / R_SUP) / (tau * tau)
def zof(ax, ay):
    """Shell height over any plan point - rotate into the owning lobe first."""
    th = math.atan2(ay, ax)
    i = math.floor((th - th0) / beta)
    a = -i * beta
    rx = ax * math.cos(a) - ay * math.sin(a)
    ry = ax * math.sin(a) + ay * math.cos(a)
    s = (rx * qy - ry * qx) / det
    t = (px * ry - py * rx) / det
    return h_crown - h_crown * (s + t) / R_SUP + gam * s * t
def r_glass(theta):
    a = ((theta - th0) % beta) / beta
    return (R_SUP + (R_TIP - R_SUP) * math.sin(math.pi * a) ** Q_BLUNT) * F_GLASS

pl = [p for p in planes if p["kind"] == "ns"][0]
n1, n2 = pl["n1"], pl["n2"]
s, e = pl["start"], pl["start"] + n1 * n2
Ux = U[s:e, 0].reshape(n1, n2)
YY = np.array(pl["a1"]); ZZ = np.array(pl["a2"])
dy, dz = YY[1] - YY[0], ZZ[1] - ZZ[0]
Q = 0.0
for i, y in enumerate(YY):
    rg = r_glass(math.pi / 2 if y >= 0 else -math.pi / 2)
    if abs(y) >= rg:
        continue
    ztop = zof(0.0, y)
    for j, z in enumerate(ZZ):
        if 0.0 < z < ztop:
            Q += -Ux[i, j] * dy * dz          # wind blows toward -x
VOL = 1494.0
print("through-flow across the x=0 interior plane : %.1f m3/s" % Q)
print("air changes per hour                       : %.1f ACH  (volume %.0f m3)"
      % (Q * 3600.0 / VOL, VOL))
print("mean interior speed on the z=1.2 m plane   : see plots")

# ---------------- redraw vertical sections with a true section aspect -------
VMAX, TMIN, TMAX = 5.0, 28.0, 34.0
def draw(pl, field, fname, title, unit, vmin, vmax, vectors=False):
    n1, n2 = pl["n1"], pl["n2"]
    s, e = pl["start"], pl["start"] + n1 * n2
    Z = field[s:e].reshape(n1, n2).T
    A1, A2 = np.array(pl["a1"]), np.array(pl["a2"])
    w = A1[-1] - A1[0]; h = A2[-1] - A2[0]
    fig, ax = plt.subplots(figsize=(13.5, 13.5 * h / w + 2.1), dpi=130)
    lv = np.linspace(vmin, vmax, 21)
    cf = ax.contourf(A1, A2, np.clip(Z, vmin, vmax), levels=lv, cmap="jet", extend="max")
    ax.contour(A1, A2, np.clip(Z, vmin, vmax), levels=lv[::4], colors="k",
               linewidths=0.3, alpha=0.35)
    if vectors:
        Ua = U[s:e, 0].reshape(n1, n2).T if pl["kind"] != "ns" else U[s:e, 1].reshape(n1, n2).T
        Ub = U[s:e, 2].reshape(n1, n2).T
        k = 3
        ax.quiver(A1[::k], A2[::k], Ua[::k, ::k], Ub[::k, ::k],
                  color="k", alpha=0.6, scale=70, width=0.0016)
    fv, uv = SPEC[pl["kind"]]
    for name, col, lw in (("shell", "#111111", 1.8), ("glazing", "#0050b0", 2.0)):
        for (p, q) in section_segments(STL[name], fv, uv):
            ax.plot([p[0], q[0]], [p[1], q[1]], color=col, lw=lw, solid_capstyle="round")
    ax.set_xlabel(pl["ax1"]); ax.set_ylabel(pl["ax2"])
    ax.set_aspect("equal"); ax.set_ylim(0, 15.2)
    ax.set_title(title, fontsize=13, pad=10)
    cb = fig.colorbar(cf, ax=ax, fraction=0.020, pad=0.012, ticks=lv[::2])
    cb.set_label(unit, fontsize=10)
    fig.text(0.012, 0.02,
             "Candela hypar shell  |  buoyantBoussinesqSimpleFoam  k-e  758k cells  |  "
             "Valencia, wind from E 4.4 m/s, outdoor 28.3 C  |  2 of 8 glazing bays open (E/W)"
             "  |  %.1f m3/s = %.1f ACH" % (Q, Q * 3600.0 / VOL), fontsize=8, color="#555555")
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    p = os.path.join(OUT, fname)
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    print("  %-30s %5.0f KB" % (fname, os.path.getsize(p) / 1024))

for pl in planes:
    if pl["kind"] == "h":
        continue
    draw(pl, UMAG, "cfd_vel_%s.png" % pl["kind"],
         "Air speed  -  %s" % pl["label"], "|U|  [m/s]", 0.0, VMAX, vectors=True)
    draw(pl, T, "cfd_temp_%s.png" % pl["kind"],
         "Air temperature  -  %s" % pl["label"], "T  [degC]", TMIN, TMAX)
