#!/bin/sh
set -eu

runs=${RUNS:-3}
out=${OUT:-experiments/pyinfra-opencode/results}
mkdir -p "$out"
mkdir -p /tmp/ansible-opencode-cp

run_one() {
    tool=$1
    iteration=$2
    log="$out/${tool}-${iteration}.log"
    start=$(python3 -c 'import time; print(time.monotonic_ns())')
    if [ "$tool" = ansible ]; then
        ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-opencode-cp \
            ansible-playbook playbooks/opencode.yml >"$log" 2>&1
    else
        pyinfra experiments/pyinfra-opencode/inventory.py experiments/pyinfra-opencode/deploy.py --limit opi -y >"$log" 2>&1
    fi
    end=$(python3 -c 'import time; print(time.monotonic_ns())')
    python3 -c "print('$tool,$iteration,' + str(($end-$start)/1e9))" >>"$out/times.csv"
}

printf 'tool,iteration,seconds\n' >"$out/times.csv"
i=1
while [ "$i" -le "$runs" ]; do
    run_one ansible "$i"
    run_one pyinfra "$i"
    i=$((i + 1))
done
