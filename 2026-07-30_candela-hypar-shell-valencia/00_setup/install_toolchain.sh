#!/usr/bin/env bash
# Toolchain installer for the environmental-analysis workflow (macOS, Apple Silicon).
# Everything here was done without any GUI installer so the setup is scriptable.
#
#   1. Ladybug Tools Grasshopper components  -> Rhino 8 UserObjects
#   2. ladybug / honeybee Python packages    -> Rhino 8 IronPython 2.7 scripts folder
#   3. Radiance 6.x (arm64 native)           -> ~/ladybug_tools/radiance
#   4. EPW weather file                      -> ~/ladybug_tools/resources/weather
#   5. OpenFOAM v2412 (arm64 native)         -> Docker image
#
# Run:  bash 00_setup/install_toolchain.sh
set -euo pipefail

RH8="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0"
GH_PLUGIN="$RH8/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)"
UO="$GH_PLUGIN/UserObjects/ladybug_tools"
SCRIPTS="$RH8/scripts"
LBT="$HOME/ladybug_tools"
STAGE="$(mktemp -d)"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> 1/5  Ladybug Grasshopper user objects"
mkdir -p "$UO"
python3 -m pip download --quiet --no-deps -d "$STAGE" \
  ladybug-grasshopper honeybee-grasshopper-radiance
( cd "$STAGE" && for w in *.whl; do unzip -oq "$w"; done )
find "$STAGE" -name "*.ghuser" -exec cp {} "$UO/" \;
echo "    installed $(ls "$UO" | wc -l | tr -d ' ') components"

echo "==> 2/5  Python stack into Rhino 8 IronPython (the LB components are GhPython)"
mkdir -p "$SCRIPTS"
python3 -m pip install --quiet --target "$STAGE/py" \
  ladybug-core ladybug-geometry ladybug-radiance ladybug-display ladybug-rhino \
  ladybug-geometry-polyskel honeybee-radiance lbt-recipes
# numpy ships as a CPython binary wheel and would shadow ladybug's pure-python
# fallbacks inside IronPython, so it is deliberately not copied.
( cd "$STAGE/py" && for d in *; do
    case "$d" in numpy|__pycache__|bin|*.dist-info|tests) continue;; esac
    rm -rf "$SCRIPTS/$d"; cp -R "$d" "$SCRIPTS/"
  done )
echo "    $(du -sh "$SCRIPTS" | cut -f1) installed"

echo "==> 3/5  Radiance (arm64 native, no Rosetta)"
URL=$(curl -sS https://api.github.com/repos/LBNL-ETA/Radiance/releases/latest \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print([a['browser_download_url'] for a in d['assets'] if a['name'].endswith('OSX_arm64.zip')][0])")
curl -sSL -o "$STAGE/rad.zip" "$URL"
rm -rf "$LBT/radiance"; mkdir -p "$LBT"
( cd "$STAGE" && unzip -q rad.zip && cp -R radiance "$LBT/radiance" )
xattr -dr com.apple.quarantine "$LBT/radiance" 2>/dev/null || true
chmod +x "$LBT/radiance/bin/"*
# ladybug_radiance finds Radiance through its own config, and the version probe
# needs RAYPATH or it cannot locate rayinit.cal
cat > "$SCRIPTS/ladybug_radiance/config.json" <<JSON
{ "radiance_path": "$LBT/radiance" }
JSON
launchctl setenv RAYPATH "$LBT/radiance/lib"
RAYPATH="$LBT/radiance/lib" "$LBT/radiance/bin/rtrace" -version

echo "==> 4/5  weather file"
mkdir -p "$LBT/resources/weather/valencia_tmyx"
cp "$HERE/weather/"* "$LBT/resources/weather/valencia_tmyx/" 2>/dev/null || \
  curl -sSL -o "$STAGE/w.zip" \
    "https://climate.onebuilding.org/WMO_Region_6_Europe/ESP_Spain/VC_Valencia/ESP_VC_Valencia.AP.082840_TMYx.2011-2025.zip" \
  && unzip -oq "$STAGE/w.zip" -d "$LBT/resources/weather/valencia_tmyx"

echo "==> 5/5  OpenFOAM image"
open -a Docker 2>/dev/null || true
for i in $(seq 1 30); do docker version >/dev/null 2>&1 && break; sleep 5; done
docker pull --platform linux/arm64 opencfd/openfoam-default:2412

rm -rf "$STAGE"
cat <<'DONE'

Done. Restart Rhino so the Ladybug tab appears in the Grasshopper ribbon
(the analysis scripts instantiate components straight from the .ghuser files,
so a restart is only needed for the ribbon).

Note: RAYPATH is set for GUI apps via `launchctl setenv`, which only affects
applications launched afterwards. Restart Rhino before running the glare study.
DONE
