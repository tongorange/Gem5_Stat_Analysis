#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
WORKSPACE=$(cd "${SCRIPT_DIR}/../.." && pwd)
RUN_ROOT="${WORKSPACE}/stats_analysis/results/raw"
RUN_TAG=${RUN_TAG:-$(date +"%Y%m%d_%H%M%S")}

UID_VAR=$(id -u)
GID_VAR=$(id -g)

GEM5_BIN=${GEM5_BIN:-"${WORKSPACE}/gem5/build/VEGA_X86/gem5.opt"}
CONFIG=${CONFIG:-"${WORKSPACE}/gem5/configs/example/apu_se.py"}
CPU_CMD=${CPU_CMD:-"${WORKSPACE}/gem5-resources/src/examples/matrix-multiply/matrix-multiply"}
GPU_CMD=${GPU_CMD:-"${WORKSPACE}/gem5-resources/src/rodinia_hip/bin/particlefilter_float"}
GPU_OPTIONS=${GPU_OPTIONS:-"-x 128 -y 128 -z 10 -np 1000"}

LLC_BLOOM_SIZE=${LLC_BLOOM_SIZE:-8192}
LLC_BLOOM_MAX=${LLC_BLOOM_MAX:-7}

EXTRA_ARGS=${EXTRA_ARGS:-""}

SCENARIOS=${SCENARIOS:-"cpu_only gpu_only cpu_gpu"}

run_one() {
  local scenario=$1
  local bloom=$2
  local outdir="${RUN_ROOT}/${RUN_TAG}_${scenario}_${bloom}"
  mkdir -p "${outdir}"

  local args=(
    "${GEM5_BIN}"
    "--outdir=${outdir}"
    "--debug-flags=RubySlicc"
    "--debug-file=debug.log"
    "--debug-start=1000000000"
    "--debug-end=2000000000"
    "${CONFIG}"
    "-n" "4" "--num-compute-units=4"
    "--single-stats-dump"
  )

  if [[ "${scenario}" == "cpu_only" ]]; then
    args+=("--cpu-cmd=${CPU_CMD}" "--cpu-only-mode")
  elif [[ "${scenario}" == "gpu_only" ]]; then
    args+=("--gpu-cmd=${GPU_CMD}" "--gpu-options=${GPU_OPTIONS}")
  else
    args+=("--cpu-cmd=${CPU_CMD}" "--gpu-cmd=${GPU_CMD}" "--gpu-options=${GPU_OPTIONS}")
  fi

  if [[ "${bloom}" == "bloom_on" ]]; then
    args+=("--llc-bloom-enable"
           "--llc-bloom-size=${LLC_BLOOM_SIZE}"
           "--llc-bloom-max-count=${LLC_BLOOM_MAX}")
  fi

  if [[ -n "${EXTRA_ARGS}" ]]; then
    # shellcheck disable=SC2206
    args+=(${EXTRA_ARGS})
  fi

  {
    echo "WORKSPACE=${WORKSPACE}"
    echo "SCENARIO=${scenario}"
    echo "BLOOM=${bloom}"
    echo "GEM5_BIN=${GEM5_BIN}"
    echo "CONFIG=${CONFIG}"
    echo "CPU_CMD=${CPU_CMD}"
    echo "GPU_CMD=${GPU_CMD}"
    echo "GPU_OPTIONS=${GPU_OPTIONS}"
    echo "LLC_BLOOM_SIZE=${LLC_BLOOM_SIZE}"
    echo "LLC_BLOOM_MAX=${LLC_BLOOM_MAX}"
    echo "EXTRA_ARGS=${EXTRA_ARGS}"
    printf "CMD: %q " "${args[@]}"
    echo
  } > "${outdir}/cmd.txt"

  docker run --rm -u "${UID_VAR}:${GID_VAR}" \
    -v "${WORKSPACE}:${WORKSPACE}" \
    -w "${WORKSPACE}" \
    ghcr.io/gem5/gcn-gpu:v24-0 \
    "${args[@]}"
}

for scenario in ${SCENARIOS}; do
  run_one "${scenario}" "bloom_off"
  run_one "${scenario}" "bloom_on"
done

echo "[INFO] Runs stored under: ${RUN_ROOT} (tag: ${RUN_TAG})"
