# WebShield Firewall — Architecture

```text
                    INTERNET
                        |
                        v
              +-------------------+
              | WebShield Host    |
              | Linux + iptables  |
              +---------+---------+
                        |
                +-------+-------+
                |               |
                v               v
             ACCEPT          DROP + LOG
                |
                v
           Protected LAN

             Admin Layer
                  |
                  v
        +---------------------+
        | Flask Dashboard     |
        | Status / Rules / UI |
        +----------+----------+
                   |
                   v
             firewall.sh
                   |
                   v
                iptables
```

## Components

- `Script/firewall.sh`: firewall policy and rule management
- `Script/web.py`: Flask monitoring/management interface
- `conf/rules.conf`: example configuration
- `logs/`: local log location
- `tests/`: basic validation scripts

## Trust Boundary

The WebShield host is the network security boundary. The dashboard should
remain bound to localhost or another explicitly protected administration
network.
