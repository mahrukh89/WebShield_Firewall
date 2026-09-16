# Security Controls

## Default-Deny
INPUT and FORWARD use a restrictive baseline; explicitly permitted traffic
is accepted while unauthorized inbound traffic is dropped.

## Stateful Filtering
Established and related connections are allowed using conntrack state.

## Port and IP Controls
Administrators can allow a TCP port or block a source IP.

## Anti-Scan Controls
The baseline includes drops for several malformed TCP flag combinations
such as NULL and FIN-style scan patterns.

## Logging
Dropped inbound traffic is rate-limited and logged with the prefix
`WEBSHIELD_DROP:`.

## Dashboard
The Flask UI exposes status/rules for local administration. Demo mode avoids
executing firewall commands and is intended for screenshots.

## Security Boundary
The project operates at the network/firewall layer. SQL injection and XSS
are application-layer issues and are **not claimed as detected/blocked by
this version**.
