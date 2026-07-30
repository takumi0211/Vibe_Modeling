#!/usr/bin/env bash
# Point-in-time glare study: 180 deg angular fisheye from inside, looking out.
# Produces a luminance HDR, a DGP figure and the false-colour map.
#
#   bash 03_glare/run_glare.sh
#
# Inputs (in rad/):
#   geometry.rad(.gz)  exported from Rhino by export_scene.py
#   materials.rad      surface properties (assumed values, see README)
#   view.txt           "px py pz  dx dy dz"  eye point and direction
#   sun.txt            "month day hour altitude azimuth DNI DHI"
set -euo pipefail
R="$HOME/ladybug_tools/radiance"
export RAYPATH="$R/lib"; export PATH="$R/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE/rad"
OUT="${1:-$HERE/../05_images/glare}"; mkdir -p "$OUT"

[ -f geometry.rad ] || gunzip -k geometry.rad.gz
read MON DAY HR ALT AZN DNI DHI < sun.txt
read VX VY VZ DX DY DZ < view.txt
AZS=$(python3 -c "print(round($AZN-180,3))")   # gendaylit wants degrees west of south

echo "==> sky  (alt $ALT, az_from_south $AZS, DNI $DNI, DHI $DHI)"
gendaylit -ang "$ALT" "$AZS" -W "$DNI" "$DHI" > sky.rad
cat >> sky.rad <<'SKY'

skyfunc glow skyglow
0
0
4 1 1 1 0
skyglow source sky
0
0
4 0 0 1 180
skyfunc glow groundglow
0
0
4 1 0.85 0.7 0
groundglow source ground
0
0
4 0 0 -1 180
SKY

echo "==> octree"
oconv materials.rad sky.rad geometry.rad > scene.oct

echo "==> rpict  (180 deg angular fisheye, 800x800)"
rpict -vta -vp $VX $VY $VZ -vd $DX $DY $DZ -vu 0 0 1 -vh 180 -vv 180 \
      -x 800 -y 800 -ab 2 -ad 1024 -as 512 -aa 0.15 -ar 128 \
      -dt 0.05 -ds 0.2 -lw 2e-5 scene.oct > lum.hdr

echo "==> evalglare"
EG=$(evalglare -d lum.hdr 2>/dev/null | tail -1)
DGP=$(echo "$EG" | awk '{print $2}'); EV=$(echo "$EG" | awk '{print $4}')
LMAX=$(evalglare -d lum.hdr 2>/dev/null | sed -n '2p' | awk '{print $11}')
printf "    DGP=%.3f  E_v=%.0f lx  L_max=%.0f cd/m2\n" "$DGP" "$EV" "$LMAX"
TXT=$(python3 -c "d=$DGP;print('imperceptible' if d<0.35 else ('disturbing' if d<0.45 else 'intolerable'))")

echo "==> figures"
pcond -h lum.hdr > vis.hdr
falsecolor -i lum.hdr -s 3000 -n 10 -l cd/m2 -lw 130 -lh 350 > fc.hdr
psign -cb 0 0 0 -cf 1 1 1 -h 26 \
  "Valencia  ${MON}/${DAY} ${HR}:00  |  DGP $(printf '%.3f' "$DGP") ($TXT)  |  E_v $(printf '%.0f' "$EV") lx  |  L_max $(printf '%.0f' "$LMAX") cd/m2" > label.hdr
pcompos -b 0 0 0 vis.hdr 0 0 fc.hdr 800 0 > pair.hdr
pcompos -b 0 0 0 label.hdr 0 800 pair.hdr 0 0 > glare.hdr
ra_bmp glare.hdr glare.bmp && sips -s format png glare.bmp --out "$OUT/glare_interior_fisheye.png" >/dev/null
ra_bmp fc.hdr fc.bmp       && sips -s format png fc.bmp    --out "$OUT/glare_luminance_falsecolor.png" >/dev/null
rm -f glare.bmp fc.bmp
echo "    wrote $OUT/glare_interior_fisheye.png"
