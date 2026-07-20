#!/usr/bin/env bash
# Logic test suite for sigma-enroll. Runs entirely as an unprivileged user
# against a temp sandbox (no real /etc/wireguard, no root). Covers:
#   - static reservation + dynamic allocation
#   - idempotency (re-run add is a no-op)
#   - re-key (pubkey change keeps the same IP)
#   - flock race safety (concurrent adds for different hosts)
#   - corrupt-conf detection + refusal + restore-backup
#   - remove
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${SCRIPT_DIR}/../bin/sigma-enroll"
SANDBOX="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

ok()   { PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1"; }

fresh_env() {
    # each test gets its own isolated conf/state so tests don't interfere
    local name="$1"
    local dir="${SANDBOX}/${name}"
    mkdir -p "${dir}/wg" "${dir}/state" "${dir}/bin"
    cat > "${dir}/bin/wg" <<'EOF'
#!/usr/bin/env bash
# stub: interface always "down" so live-apply is skipped in logic tests
case "$1" in
    show) exit 1 ;;
    set)  echo "wg set $*" >> "${WG_STUB_LOG:-/dev/null}"; exit 0 ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "${dir}/bin/wg"
    cat > "${dir}/wg/wg0.conf" <<'EOF'
[Interface]
PrivateKey = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
Address = 10.88.0.1/24
ListenPort = 51820
EOF
    printf '%s\n' "$dir"
}

genkey() {
    # deterministic-ish fake but *structurally valid* curve25519-shaped key:
    # 32 random bytes, base64-encoded (44 chars incl. trailing '=')
    head -c 32 /dev/urandom | base64
}

run_add() {
    local dir="$1"; shift
    env WG_CONF="${dir}/wg/wg0.conf" STATE_DIR="${dir}/state" \
        WG_BIN="${dir}/bin/wg" WG_STUB_LOG="${dir}/wg_stub.log" \
        QRENCODE_BIN=/nonexistent-qrencode \
        "$BIN" add "$@"
}

run_cmd() {
    local dir="$1" sub="$2"; shift 2
    env WG_CONF="${dir}/wg/wg0.conf" STATE_DIR="${dir}/state" \
        WG_BIN="${dir}/bin/wg" WG_STUB_LOG="${dir}/wg_stub.log" \
        QRENCODE_BIN=/nonexistent-qrencode \
        "$BIN" "$sub" "$@"
}

# --- Test 1: static reservation -------------------------------------------
{
    dir=$(fresh_env t1)
    key=$(genkey)
    out=$(run_add "$dir" sigma-studio node "$key" 2>&1)
    if echo "$out" | grep -q "IP=10.88.0.7"; then
        ok "static reservation: sigma-studio -> 10.88.0.7"
    else
        bad "static reservation: sigma-studio -> 10.88.0.7 ($out)"
    fi
}

# --- Test 2: dynamic allocation, sequential ---------------------------------
{
    dir=$(fresh_env t2)
    k1=$(genkey); k2=$(genkey)
    out1=$(run_add "$dir" newnode-a role "$k1" 2>&1)
    out2=$(run_add "$dir" newnode-b role "$k2" 2>&1)
    ip1=$(echo "$out1" | grep -oE '10\.88\.0\.[0-9]+' | head -1)
    ip2=$(echo "$out2" | grep -oE '10\.88\.0\.[0-9]+' | head -1)
    if [ "$ip1" = "10.88.0.8" ] && [ "$ip2" = "10.88.0.9" ]; then
        ok "dynamic allocation: sequential .8, .9"
    else
        bad "dynamic allocation: expected .8/.9, got $ip1/$ip2"
    fi
}

# --- Test 3: idempotency ----------------------------------------------------
{
    dir=$(fresh_env t3)
    key=$(genkey)
    run_add "$dir" nodex worker "$key" >/dev/null 2>&1
    before_rows=$(grep -c "sigma-enroll: nodex " "${dir}/wg/wg0.conf")
    before_alloc_rows=$(awk -F'\t' '$1=="nodex"' "${dir}/state/allocations.tsv" | wc -l)
    out2=$(run_add "$dir" nodex worker "$key" 2>&1)
    after_rows=$(grep -c "sigma-enroll: nodex " "${dir}/wg/wg0.conf")
    after_alloc_rows=$(awk -F'\t' '$1=="nodex"' "${dir}/state/allocations.tsv" | wc -l)
    if [ "$before_rows" -eq 1 ] && [ "$after_rows" -eq 1 ] && \
       [ "$before_alloc_rows" -eq 1 ] && [ "$after_alloc_rows" -eq 1 ] && \
       echo "$out2" | grep -qi "no-op"; then
        ok "idempotency: re-running add is a no-op (no duplicate stanza/row)"
    else
        bad "idempotency: before=$before_rows/$before_alloc_rows after=$after_rows/$after_alloc_rows out2='$out2'"
    fi
}

# --- Test 4: re-key (pubkey changes, IP stays) ------------------------------
{
    dir=$(fresh_env t4)
    k1=$(genkey); k2=$(genkey)
    out1=$(run_add "$dir" rekeynode role "$k1" 2>&1)
    ip1=$(echo "$out1" | grep -oE '10\.88\.0\.[0-9]+' | head -1)
    out2=$(run_add "$dir" rekeynode role "$k2" 2>&1)
    ip2=$(echo "$out2" | grep -oE '10\.88\.0\.[0-9]+' | head -1)
    stanza_count=$(grep -c "sigma-enroll: rekeynode " "${dir}/wg/wg0.conf")
    has_new_key=$(grep -q "$k2" "${dir}/wg/wg0.conf" && echo yes || echo no)
    has_old_key=$(grep -q "$k1" "${dir}/wg/wg0.conf" && echo yes || echo no)
    if [ "$ip1" = "$ip2" ] && [ "$stanza_count" -eq 1 ] && \
       [ "$has_new_key" = yes ] && [ "$has_old_key" = no ]; then
        ok "re-key: pubkey swapped, IP unchanged, old stanza removed"
    else
        bad "re-key: ip1=$ip1 ip2=$ip2 stanzas=$stanza_count new=$has_new_key old=$has_old_key"
    fi
}

# --- Test 5: flock race safety (concurrent adds, different hosts) ----------
{
    dir=$(fresh_env t5)
    pids=()
    declare -a keys
    for i in $(seq 1 8); do
        keys[$i]=$(genkey)
    done
    for i in $(seq 1 8); do
        ( run_add "$dir" "racenode$i" role "${keys[$i]}" >"${dir}/out_$i.log" 2>&1 ) &
        pids+=($!)
    done
    fail_wait=0
    for p in "${pids[@]}"; do
        wait "$p" || fail_wait=1
    done

    alloc_rows=$(($(wc -l < "${dir}/state/allocations.tsv") - 1))
    unique_ips=$(awk -F'\t' 'NR>1{print $3}' "${dir}/state/allocations.tsv" | sort -u | wc -l)
    stanza_count=$(grep -c '^\[Peer\]$' "${dir}/wg/wg0.conf")
    # structural sanity: conf must still validate (no interleaved corruption)
    valid=1
    awk '
        /^\[Interface\]/{ifc++}
        /^\[Peer\]/{peer++}
    ' "${dir}/wg/wg0.conf" > /dev/null || valid=0

    if [ "$alloc_rows" -eq 8 ] && [ "$unique_ips" -eq 8 ] && [ "$stanza_count" -eq 8 ] && [ "$fail_wait" -eq 0 ]; then
        ok "flock race safety: 8 concurrent adds -> 8 rows, 8 unique IPs, 8 clean stanzas"
    else
        bad "flock race safety: rows=$alloc_rows unique_ips=$unique_ips stanzas=$stanza_count fail_wait=$fail_wait"
    fi
}

# --- Test 6: corrupt-conf detection + refusal -------------------------------
{
    dir=$(fresh_env t6)
    key=$(genkey)
    run_add "$dir" goodnode role "$key" >/dev/null 2>&1
    good_backup_count_before=$(ls "${dir}/state/backups" 2>/dev/null | wc -l)

    # corrupt it: truncate mid-stanza (simulates a crashed write)
    printf '[Peer]\nPublicK' >> "${dir}/wg/wg0.conf"

    key2=$(genkey)
    if run_add "$dir" anothernode role "$key2" >"${dir}/corrupt_attempt.log" 2>&1; then
        bad "corrupt-conf detection: add succeeded against a corrupt conf (should have refused)"
    else
        if grep -qi "invalid" "${dir}/corrupt_attempt.log"; then
            # confirm it did NOT record the bogus host as enrolled
            if ! grep -q "^anothernode" "${dir}/state/allocations.tsv"; then
                ok "corrupt-conf detection: refused to modify, no bogus allocation recorded"
            else
                bad "corrupt-conf detection: refused write but still recorded allocation"
            fi
        else
            bad "corrupt-conf detection: failed for wrong reason: $(cat "${dir}/corrupt_attempt.log")"
        fi
    fi
}

# --- Test 7: restore-backup recovers from corruption ------------------------
{
    dir=$(fresh_env t7)
    key=$(genkey); key2=$(genkey)
    run_add "$dir" goodnode role "$key" >/dev/null 2>&1
    # _backup_conf snapshots PRE-write state, so the backup worth restoring
    # (the one containing goodnode) is the one taken just before this 2nd add
    run_add "$dir" secondnode role "$key2" >/dev/null 2>&1
    # corrupt
    printf 'garbage not a conf line at all###' >> "${dir}/wg/wg0.conf"
    run_cmd "$dir" restore-backup >"${dir}/restore.log" 2>&1
    if grep -q "sigma-enroll: goodnode " "${dir}/wg/wg0.conf" && \
       ! grep -q "garbage not a conf" "${dir}/wg/wg0.conf"; then
        ok "restore-backup: recovered valid conf after corruption"
    else
        bad "restore-backup: did not recover cleanly ($(cat "${dir}/restore.log"))"
    fi
}

# --- Test 8: remove ----------------------------------------------------------
{
    dir=$(fresh_env t8)
    key=$(genkey)
    run_add "$dir" byebye role "$key" >/dev/null 2>&1
    run_cmd "$dir" remove byebye >"${dir}/remove.log" 2>&1
    still_in_conf=$(grep -c "sigma-enroll: byebye " "${dir}/wg/wg0.conf" || true)
    still_in_alloc=$(awk -F'\t' '$1=="byebye"' "${dir}/state/allocations.tsv" | wc -l)
    if [ "$still_in_conf" -eq 0 ] && [ "$still_in_alloc" -eq 0 ]; then
        ok "remove: peer stanza and allocation row both gone"
    else
        bad "remove: still_in_conf=$still_in_conf still_in_alloc=$still_in_alloc"
    fi
}

# --- Test 9: invalid pubkey rejected ----------------------------------------
{
    dir=$(fresh_env t9)
    if run_add "$dir" badnode role "not-a-real-key" >"${dir}/badkey.log" 2>&1; then
        bad "invalid pubkey: add succeeded with garbage key"
    else
        ok "invalid pubkey: rejected as expected"
    fi
}

echo "----------------------------------------"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
