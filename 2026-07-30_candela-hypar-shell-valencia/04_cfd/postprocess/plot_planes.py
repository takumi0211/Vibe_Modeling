import os, sys, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.dirname(HERE)                    # 04_cfd/
PROJ = os.path.dirname(SC)
OUT = os.path.join(PROJ, "05_images", "cfd")
DATA = os.path.join(SC, "results")            # U and T probe dumps

# ---------- read probe output ----------
def last_line(path):
    with open(path) as fh:
        line = None
        for l in fh:
            if not l.startswith("#"):
                line = l
        return line

def read_vec(path):
    l = last_line(path)
    vals = []
    for chunk in l.split("(")[1:]:
        a, b, c = chunk.split(")")[0].split()
        vals.append((float(a), float(b), float(c)))
    return np.array(vals)

def read_sca(path):
    l = last_line(path)
    return np.array([float(x) for x in l.split()[1:]])

U = read_vec(os.path.join(DATA, "U"))
T = read_sca(os.path.join(DATA, "T")) - 273.15
UMAG = np.linalg.norm(U, axis=1)
planes = json.load(open(os.path.join(HERE, "planes.json")))["planes"]
print("read %d probe values" % len(UMAG))

# ---------- STL section outlines ----------
def load_stl(path):
    tris, cur = [], []
    for line in open(path):
        s = line.strip()
        if s.startswith("vertex"):
            cur.append([float(v) for v in s.split()[1:4]])
            if len(cur) == 3:
                tris.append(cur); cur = []
    return np.array(tris)

STL = {n: load_stl(os.path.join(SC, "stl", n + ".stl"))
       for n in ("shell", "glazing")}
print("stl tris:", {k: len(v) for k, v in STL.items()})

def section_segments(tris, fval, to_uv):
    """Intersect triangles with the plane f(p)=0; return 2D segments."""
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

def outline_for(pl):
    if pl["kind"] == "h":
        z = pl["z"]
        fv = lambda P: P[:, 2] - z
        uv = lambda p: (p[0], p[1])
    elif pl["kind"] == "ew":
        fv = lambda P: P[:, 1]
        uv = lambda p: (p[0], p[2])
    elif pl["kind"] == "ns":
        fv = lambda P: P[:, 0]
        uv = lambda p: (p[1], p[2])
    else:
        fv = lambda P: P[:, 1] - P[:, 0]
        uv = lambda p: (p[0] * math.sqrt(2.0), p[2])
    return {k: section_segments(v, fv, uv) for k, v in STL.items()}

# ---------- Flow Designer flavoured plot ----------
VMAX, TMIN, TMAX = 5.0, 28.0, 36.0

def draw(pl, field, fname, title, unit, cmap, vmin, vmax, vectors=False):
    n1, n2 = pl["n1"], pl["n2"]
    s, e = pl["start"], pl["start"] + n1 * n2
    Z = field[s:e].reshape(n1, n2).T
    A1 = np.array(pl["a1"]); A2 = np.array(pl["a2"])
    fig, ax = plt.subplots(figsize=(9.6, 7.4), dpi=130)
    lv = np.linspace(vmin, vmax, 21)
    cf = ax.contourf(A1, A2, np.clip(Z, vmin, vmax), levels=lv, cmap=cmap, extend="max")
    ax.contour(A1, A2, np.clip(Z, vmin, vmax), levels=lv[::4], colors="k",
               linewidths=0.3, alpha=0.35)
    if vectors:
        Ux = U[s:e, 0].reshape(n1, n2).T
        Uy = U[s:e, 1].reshape(n1, n2).T
        k = 5
        ax.quiver(A1[::k], A2[::k], Ux[::k, ::k], Uy[::k, ::k],
                  color="k", alpha=0.55, scale=60, width=0.0022)
    out = outline_for(pl)
    for name, col, lw in (("shell", "#111111", 1.6), ("glazing", "#0050b0", 1.9)):
        for (p, q) in out[name]:
            ax.plot([p[0], q[0]], [p[1], q[1]], color=col, lw=lw, solid_capstyle="round")
    ax.set_xlabel(pl["ax1"]); ax.set_ylabel(pl["ax2"])
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=12, pad=10)
    ax.tick_params(labelsize=9)
    for sp in ax.spines.values():
        sp.set_linewidth(0.8)
    cb = fig.colorbar(cf, ax=ax, fraction=0.042, pad=0.02, ticks=lv[::2])
    cb.set_label(unit, fontsize=10)
    cb.ax.tick_params(labelsize=9)
    fig.text(0.012, 0.014,
             "Candela hypar shell  |  buoyantBoussinesqSimpleFoam  k-e  758k cells  |  "
             "Valencia, wind from E 4.4 m/s, outdoor 28.3 C  |  2 of 8 glazing bays open (E/W)",
             fontsize=7, color="#555555")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p = os.path.join(OUT, fname)
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    print("  %-42s %6.0f KB" % (fname, os.path.getsize(p) / 1024))

n = 0
for pl in planes:
    tag = ("z%03d" % round(pl["z"] * 10)) if pl["kind"] == "h" else pl["kind"]
    horiz = pl["kind"] == "h"
    draw(pl, UMAG, "cfd_vel_%s.png" % tag,
         "Air speed  -  %s" % pl["label"], "|U|  [m/s]", "jet", 0.0, VMAX,
         vectors=horiz)
    draw(pl, T, "cfd_temp_%s.png" % tag,
         "Air temperature  -  %s" % pl["label"], "T  [degC]", "jet", TMIN, TMAX)
    n += 2
print("total %d images" % n)
