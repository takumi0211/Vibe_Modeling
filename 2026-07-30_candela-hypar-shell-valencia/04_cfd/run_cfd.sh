#!/usr/bin/env bash
# Natural-ventilation CFD: wind + buoyancy, steady RANS.
#
#   bash 04_cfd/run_cfd.sh
#
# Pipeline: blockMesh -> decomposePar -> snappyHexMesh (parallel, zero-thickness
# baffles) -> reconstruct -> re-decompose -> buoyantBoussinesqSimpleFoam -> probes.
#
# The re-decomposition is not optional: snappyHexMesh creates the shell/glazing
# baffle patches (and their _slave twins) only after the fields have already been
# decomposed, so the processor field files would be missing those patch entries.
set -euo pipefail
IMG=opencfd/openfoam-default:2412
NP=8
HERE="$(cd "$(dirname "$0")" && pwd)"
CASE="$HERE/case"

mkdir -p "$CASE/constant/triSurface"
cp "$HERE/stl/shell.stl" "$HERE/stl/glazing.stl" "$CASE/constant/triSurface/"

run() { docker run --rm --platform linux/arm64 -v "$CASE":/case "$IMG" bash -lc "cd /case && $1"; }

echo "==> blockMesh"
run "blockMesh > log.blockMesh 2>&1 && tail -3 log.blockMesh"

echo "==> snappyHexMesh (${NP} ranks)"
run "decomposePar -force > log.decomposePar 2>&1 &&
     mpirun --allow-run-as-root -np $NP snappyHexMesh -overwrite -parallel > log.snappy 2>&1 &&
     tail -3 log.snappy"

echo "==> reconstruct + re-decompose so the baffle patches reach the fields"
run "reconstructParMesh -constant > log.reconstruct 2>&1 && rm -rf processor* &&
     decomposePar -force > log.decomposePar2 2>&1 &&
     grep -E '^ +[A-Za-z_]+\$' constant/polyMesh/boundary | tr -d ' '"

echo "==> buoyantBoussinesqSimpleFoam (900 iterations, ~10 min on 8 ranks)"
run "mpirun --allow-run-as-root -np $NP buoyantBoussinesqSimpleFoam -parallel > log.solve 2>&1;
     grep -E '^Time = ' log.solve | tail -1; grep '^ExecutionTime' log.solve | tail -1"

echo "==> sample the section planes"
run "mpirun --allow-run-as-root -np $NP postProcess -func sampleDict -latestTime -parallel > log.sample 2>&1 &&
     ls postProcessing/sampleDict/*"

cp "$CASE"/postProcessing/sampleDict/*/U "$HERE/results/U"
cp "$CASE"/postProcessing/sampleDict/*/T "$HERE/results/T"

echo "==> plots"
cd "$HERE/postprocess"
python3 plot_planes.py
python3 plot_sections.py
echo "done."
