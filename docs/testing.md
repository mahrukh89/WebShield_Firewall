# Testing & Validation

All testing must be performed in an authorized isolated lab.

## Test 01 — Status

```bash
sudo ./Script/firewall.sh status
```

Expected: current policies and rule information are displayed.

## Test 02 — Allow Port

```bash
sudo ./Script/firewall.sh allow-port 8080
sudo ./Script/firewall.sh list
```

Expected: a TCP/8080 rule appears.

## Test 03 — Block Source IP

```bash
sudo ./Script/firewall.sh block-ip 203.0.113.45
sudo ./Script/firewall.sh list
```

Expected: a DROP rule for the source appears.

## Test 04 — Logging

Inspect the system log location configured by your distribution. If the
kernel logging path is configured for WebShield, look for the
`WEBSHIELD_DROP:` prefix.

## Test 05 — Dashboard

```bash
WEBSHIELD_DEMO=1 python3 Script/web.py
```

Open `http://127.0.0.1:5000/dashboard`.

Expected: dashboard loads without changing firewall rules.

## Test 06 — Persistence

```bash
sudo ./Script/firewall.sh save
sudo ./Script/firewall.sh restore
```

Expected: saved rules can be restored.

## Validation Record

| Test | Expected | Actual |
|---|---|---|
| Firewall status | Policies shown | [FILL IN] |
| Port allow | Rule added | [FILL IN] |
| IP block | Rule added | [FILL IN] |
| Logging | Drop recorded | [FILL IN] |
| Dashboard | Loads | [FILL IN] |
| Persistence | Rules restored | [FILL IN] |

Only replace `[FILL IN]` with results you actually observed.
