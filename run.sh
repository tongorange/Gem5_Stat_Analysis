#!/usr/bin/env bash

# ========== 原有变量和参数保持不变 ==========
workspace=${workspace:-/home/chengt/gem5-workspace}
GEM5=${GEM5:-$workspace/gem5/build/VEGA_X86/gem5.opt}
CONF=${CONF:-$workspace/gem5/configs/example/apu_se_origin.py}
RODINIA=${RODINIA:-$workspace/gem5-resources/src/rodinia_hip}
RODINIA_BIN=${RODINIA_BIN:-${RODINIA}/bin}
RODINIA_DATA=${RODINIA_DATA:-${RODINIA}/data}
OUTDIR_PREFIX=${OUTDIR_PREFIX:-$workspace/stats_analysis/results/raw}

GEM5_PARAMS=(
    "-r"
    "-e"
    "--debug-flags=RubySlicc"
    "--debug-file=debug.log"
    "--debug-start=1000000000"
    "--debug-end=2000000000"
)

PARAMS=(
    "-n=4"
    "-u=4"
    "--tcp-size=16kB"
    "--tcp-assoc=4"
    "--TCP_latency=4"
    "--tcc-size=512kB"
    "--tcc-assoc=16"
    "--TCC_latency=20"
    "--cpu-to-dir-latency=10"
    "--gpu-to-dir-latency=30"
    "--mem-size=8GiB"
    "--cpu-type=X86O3CPU"
)

echo "Using parameters: ${PARAMS[@]}"
CONFIG=${CONFIG:-"default"}
PARALLEL_JOBS=${PARALLEL_JOBS:-4}
CORES=$(nproc 2>/dev/null || echo 4)
if [ "$PARALLEL_JOBS" -gt "$CORES" ]; then
    PARALLEL_JOBS=$CORES
    echo "Warning: limiting PARALLEL_JOBS to $CORES"
fi

# ========== Benchmark functions ==========
# 注意：这些函数不会被直接调用，只用于生成命令字符串

btree() {
  echo "$GEM5 -d $OUTDIR_PREFIX/btree_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/b+tree.out \
        --options=\"file $RODINIA_DATA/b+tree/mil.txt command $RODINIA_DATA/b+tree/command.txt\""
}

bfs() {
  echo "$GEM5 -d $OUTDIR_PREFIX/bfs_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/bfs.out \
        --options=\"file $RODINIA_DATA/bfs/graph65536.txt\""
}

dwt2d() {
  echo "$GEM5 -d $OUTDIR_PREFIX/dwt2d_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/dwt2d \
        --options=\"192.bmp -d 192x192 -f -5 -l 3\""
}

gaussian() {
  echo "$GEM5 -d $OUTDIR_PREFIX/gaussian_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/gaussian \
        --options=\"-f $RODINIA_DATA/gaussian/matrix4.txt\""
}

hotspot() {
  echo "$GEM5 -d $OUTDIR_PREFIX/hotspot_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/hotspot \
        --options=\"512 2 2 $RODINIA_DATA/hotspot/temp_512 $RODINIA_DATA/hotspot/power_512 output.out\""
}

lavaMD() {
  echo "$GEM5 -d $OUTDIR_PREFIX/lavaMD_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/lavaMD \
        --options=\"-boxes1d 10\""
}

nn() {
  echo "mkdir -p $OUTDIR_PREFIX/nn_$CONFIG && \
        printf \"${RODINIA_DATA}/nn/cane4_0.db\n${RODINIA_DATA}/nn/cane4_1.db\n${RODINIA_DATA}/nn/cane4_2.db\n${RODINIA_DATA}/nn/cane4_3.db\" > $OUTDIR_PREFIX/nn_$CONFIG/filelist.txt && \
        $GEM5 -d $OUTDIR_PREFIX/nn_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/nn \
        --options=\"filelist.txt -r 5 -lat 30 -lng 90\""
}

nw() {
  echo "$GEM5 -d $OUTDIR_PREFIX/nw_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/needle \
        --options=\"2048 10\""
}

particlefilter() {
  echo "$GEM5 -d $OUTDIR_PREFIX/particlefilter_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/particlefilter_float \
        --options=\"-x 128 -y 128 -z 10 -np 1000\""
}

pathfinder() {
  echo "$GEM5 -d $OUTDIR_PREFIX/pathfinder_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $CONF ${PARAMS[*]} \
        --cmd $RODINIA_BIN/pathfinder \
        --options=\"100000 100 20\""
}

hetero() {
  echo "$GEM5 -d $OUTDIR_PREFIX/hetero_$CONFIG \
        ${GEM5_PARAMS[*]} \
        $workspace/gem5/configs/example/apu_se.py ${PARAMS[*]} \
        --cpu-cmd=$workspace/gem5-resources/src/examples/matrix-multiply/matrix-multiply \
        --gpu-cmd=$RODINIA_BIN/bfs.out"
}

# ========== 调度逻辑 ==========
all=("btree" "bfs" "dwt2d" "gaussian" "hotspot" "lavaMD" "nn" "nw" "particlefilter" "pathfinder" "hetero")

BENCHMARK=$1

if [[ " ${all[*]} " =~ " ${BENCHMARK} " ]]; then
    # 单独运行：直接执行原函数（兼容旧用法）
    eval "$($BENCHMARK)"
elif [ "$BENCHMARK" == "all" ]; then
    echo "Running all benchmarks with $PARALLEL_JOBS concurrent jobs"
    
    TMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TMP_DIR"' EXIT
    
    # 为每个 benchmark 生成可执行脚本
    for bench in "${all[@]}"; do
        script="$TMP_DIR/run_${bench//+/plus}.sh"  # 替换 + 为 plus 避免文件名问题
        cmd=$($bench)  # 获取命令字符串
        cat > "$script" <<EOF
#!/usr/bin/env bash
set -e
cd "$workspace" || exit 1
$cmd
EOF
        chmod +x "$script"
    done
    
    # 并行执行
    find "$TMP_DIR" -name "*.sh" | xargs -P "$PARALLEL_JOBS" -I {} bash {}
    
    echo "All benchmarks finished"
else
    echo "Unknown benchmark: $BENCHMARK"
    exit 1
fi