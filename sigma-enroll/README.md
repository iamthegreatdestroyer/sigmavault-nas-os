# sigma-enroll

Race-free wg0 peer enrollment for the Sigma mesh. Replaces the manual
"keygen + hand-edit wg0.conf + wg set" runbook used to join sigma-studio
and sigma-pi with a single idempotent command on the hub.

## Components

- `bin/sigma-enroll` — hub-side CLI. `add <hostname> <role> <pubkey>`,
  `list`, `remove <hostname>`, `restore-backup`.
- `bin/sigma-firstboot` — node-side helper. Generates a keypair (private
  key never leaves the node), prints the pubkey + QR for handoff, waits
  for the hub's returned conf fragment, assembles the final wg0.conf,
  brings the interface up, and forces an immediate `unattended-upgrade`
  check (fixes the enrollment deadlock: a fresh node's first scheduled
  update run is hours out, but it has no route to the mirrors until wg0
  is confirmed live — so don't wait for the timer).
- `systemd/sigma-firstboot-enroll-wait.service` — runs `sigma-firstboot`
  once on first boot (guarded by `ConditionPathExists=!/etc/wireguard/wg0.conf`).

## Design invariants

- **Never calls `wg-quick save`.** That command rewrites wg0.conf from the
  live interface state and strips the `# sigma-enroll: <hostname> ...`
  comments this tool uses for idempotency and removal. All edits are
  direct: read → validate → append/splice → validate → atomic `mv`.
- **Every write is preceded by a validation of the existing file and
  followed by a validation of the new file.** If either fails, the
  operation aborts and nothing is modified. A timestamped backup is taken
  before every write regardless, so `restore-backup` is always available.
- **flock-protected.** The whole allocate → write → record sequence for
  `add`/`remove` runs under an exclusive lock on `allocations.lock`, so
  concurrent enrollments can't race each other into a corrupt conf or a
  double-allocated IP.
- **Static reservations honored first.** `reservations.tsv` seeds the
  known hosts (sigma-box=.1, sigma-pi=.2, sigma-windows=.3, sigma-forge=.5,
  sigma-infer=.6, sigma-studio=.7); anything else gets the next free IP
  from the dynamic pool (.8–.254).
- **Re-running `add` with the same hostname+pubkey is a no-op** (it
  self-heals a missing peer stanza or missing live-apply if needed, but
  makes no changes when everything already matches).
- **Private keys never transit the hub.** The node generates its own
  keypair locally; only the public key crosses the wire/QR/console.

## Usage

On the hub:

```
sigma-enroll add sigma-newnode worker <pubkey-from-node>
sigma-enroll list
sigma-enroll remove sigma-newnode
sigma-enroll restore-backup            # restores most recent backup
```

On a new node (first boot, or manually):

```
sudo sigma-firstboot
```

It prints the pubkey/QR, then waits. On the hub, run `sigma-enroll add`
with that pubkey — the node conf snippet lands in
`/etc/sigma-enroll/nodes/<hostname>.conf`; copy/scp its `[Peer]` block +
assigned `Address` to the node's `/etc/wireguard/wg0.conf.fragment`, and
`sigma-firstboot` picks it up, brings the interface up, and forces an
immediate update check.

## Testing

`tests/test_sigma_enroll.sh` is a pure-bash logic suite — no root, no real
`/etc/wireguard`, no real `wg` binary (a stub is injected via `WG_BIN`).
Covers: static reservation, dynamic sequential allocation, idempotency,
re-key (pubkey change, IP unchanged), flock race safety (8 concurrent
`add` calls for distinct hosts), corrupt-conf detection + refusal,
`restore-backup` recovery, `remove`, and invalid-pubkey rejection.

```
bash tests/test_sigma_enroll.sh
```

**Not covered by the logic suite (needs root):** actual `wg set` live-apply
against a real interface, and a genuine end-to-end handshake test. Both
require root on the hub, which `stevo` does not have passwordless — see
the deployment section below.

## Deployment (requires root — not automatable over SSH without a password prompt)

```
sudo install -m 755 bin/sigma-enroll /usr/local/bin/sigma-enroll
sudo install -m 755 bin/sigma-firstboot /usr/local/bin/sigma-firstboot
sudo install -m 644 systemd/sigma-firstboot-enroll-wait.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Before first production use, capture the hub's own pubkey for
`sigma-firstboot` to embed in node confs:

```
sudo cp /etc/wireguard/publickey /etc/sigma-enroll/hub.pubkey
```

### Recommended live E2E test (throwaway peer, before trusting this on a
real device)

Spin up a disposable network namespace or container with its own wg
keypair, run `sigma-enroll add throwaway-test test <pubkey>` on the hub,
confirm a real handshake (`wg show wg0 latest-handshakes`), then
`sigma-enroll remove throwaway-test`.
