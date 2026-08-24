#!/usr/bin/env python3
"""
WebShield Firewall - web.py
Flask dashboard that wraps firewall.sh: view status, rules, logs,
and add/remove rules from the browser.

Run:
    sudo python3 web.py
Then open http://127.0.0.1:5000/dashboard
"""

import os
import re
import subprocess
from datetime import datetime

from flask import Flask, render_template_string, request, redirect, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIREWALL_SCRIPT = os.path.join(BASE_DIR, "firewall.sh")
LOG_FILE = "/var/log/webshield_firewall.log"

# Demo mode lets the dashboard run without root/iptables (e.g. for a public
# portfolio deploy or to generate documentation screenshots). It serves
# realistic sample output instead of calling firewall.sh.
DEMO_MODE = os.environ.get("WEBSHIELD_DEMO", "0") == "1"

app = Flask(__name__)
app.secret_key = os.environ.get("WEBSHIELD_SECRET", "dev-secret-change-me")

DEMO_STATUS = (
    "=== WebShield Firewall Status ===\n"
    "Policy INPUT:   Chain INPUT (policy DROP)\n"
    "Policy FORWARD: Chain FORWARD (policy DROP)\n"
    "Policy OUTPUT:  Chain OUTPUT (policy ACCEPT)\n"
    "Active rules (INPUT): 8\n"
    "IP forwarding: 1\n"
)

DEMO_RULES = (
    "Chain INPUT (policy DROP 0 packets, 0 bytes)\n"
    "num  pkts bytes target  prot opt in  out  source            destination\n"
    "1    1256  102K ACCEPT  tcp  --  lo  *    0.0.0.0/0         0.0.0.0/0     tcp dpt:22\n"
    "2     843   68K ACCEPT  tcp  --  lo  *    0.0.0.0/0         0.0.0.0/0     tcp dpt:80\n"
    "3     671   54K ACCEPT  tcp  --  lo  *    0.0.0.0/0         0.0.0.0/0     tcp dpt:443\n"
    "4       0    0B DROP    all  --  *   *    203.0.113.45      0.0.0.0/0     /* Blocked IP */\n"
    "5      12  720B DROP    tcp  --  *   *    0.0.0.0/0         0.0.0.0/0     tcp dpt:23\n"
    "\n"
    "Chain FORWARD (policy DROP 0 packets, 0 bytes)\n"
    "num  pkts bytes target  prot opt in    out   source          destination\n"
    "1    2451  198K ACCEPT  all  --  eth1  eth0  192.168.1.0/24  0.0.0.0/0\n"
    "2     936   74K ACCEPT  all  --  eth0  eth1  0.0.0.0/0       192.168.1.0/24  state RELATED,ESTABLISHED\n"
)

DEMO_LOGS = [
    "2026-08-25 14:31:58 | BLOCK ip 203.0.113.45\n",
    "2026-08-25 14:31:32 | BLOCK port 23/tcp\n",
    "2026-08-25 13:52:10 | ALLOW port 8080/tcp\n",
    "2026-08-25 13:40:02 | Firewall initialized with default policy DROP (INPUT/FORWARD).\n",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_firewall(*args):
    """Run firewall.sh with args, return (success, output)."""
    if DEMO_MODE:
        return _demo_response(args)
    try:
        result = subprocess.run(
            ["sudo", FIREWALL_SCRIPT, *args],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "firewall.sh not found. Check FIREWALL_SCRIPT path."
    except subprocess.TimeoutExpired:
        return False, "Command timed out."


def _demo_response(args):
    cmd = args[0] if args else ""
    if cmd == "status":
        return True, DEMO_STATUS
    if cmd == "list":
        return True, DEMO_RULES
    if cmd in ("allow-port", "block-port", "block-ip", "unblock-ip"):
        target = args[1] if len(args) > 1 else "?"
        return True, f"[demo mode] {cmd} {target} — no changes were applied to a real firewall.\n"
    return True, "[demo mode] command simulated.\n"


def get_status():
    ok, out = run_firewall("status")
    info = {"raw": out, "input_policy": "UNKNOWN", "rule_count": "0"}
    for line in out.splitlines():
        if line.startswith("Policy INPUT:"):
            m = re.search(r"policy (\w+)", line)
            if m:
                info["input_policy"] = m.group(1)
        if line.startswith("Active rules"):
            m = re.search(r": (\d+)", line)
            if m:
                info["rule_count"] = m.group(1)
    return info


def get_rules():
    ok, out = run_firewall("list")
    return out if ok else "Could not read rules (is the app running with sudo?)."


def get_logs(limit=50):
    if DEMO_MODE:
        return DEMO_LOGS[:limit]
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()[-limit:]
    return list(reversed(lines))


# ---------------------------------------------------------------------------
# Templates (single-file, inline, dark theme to match the mockup)
# ---------------------------------------------------------------------------

BASE_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>WebShield Firewall</title>
<style>
  :root{
    --bg:#0d1117; --panel:#161b22; --border:#21262d;
    --text:#e6edf3; --muted:#8b949e; --accent:#3fb950;
    --danger:#f85149; --info:#58a6ff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
       font-family:-apple-system,Segoe UI,Roboto,sans-serif}
  .layout{display:flex;min-height:100vh}
  nav{width:220px;background:var(--panel);border-right:1px solid var(--border);
      padding:20px 0;flex-shrink:0}
  nav .brand{padding:0 20px 20px;font-weight:700;font-size:18px;
             border-bottom:1px solid var(--border);margin-bottom:10px}
  nav a{display:block;padding:10px 20px;color:var(--muted);text-decoration:none;font-size:14px}
  nav a:hover, nav a.active{background:#1f2937;color:var(--text)}
  main{flex:1;padding:30px 40px}
  h1{margin:0 0 6px}
  .sub{color:var(--muted);margin-bottom:24px}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px}
  .card .label{color:var(--muted);font-size:13px}
  .card .value{font-size:28px;font-weight:700;margin-top:4px}
  .ok{color:var(--accent)}
  table{width:100%;border-collapse:collapse;background:var(--panel);
        border:1px solid var(--border);border-radius:10px;overflow:hidden}
  th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--border);font-size:13px}
  th{color:var(--muted);font-weight:600}
  pre{background:var(--panel);border:1px solid var(--border);border-radius:10px;
      padding:16px;overflow:auto;font-size:13px;color:#c9d1d9}
  .badge{padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600}
  .allow{background:#123822;color:var(--accent)}
  .block{background:#3a1618;color:var(--danger)}
  form.inline{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
  input,select{background:#0d1117;border:1px solid var(--border);color:var(--text);
               padding:8px 10px;border-radius:6px}
  button{background:var(--accent);color:#04220f;border:none;padding:8px 16px;
         border-radius:6px;font-weight:600;cursor:pointer}
  button.danger{background:var(--danger);color:#2c0a0a}
  .flash{padding:10px 14px;border-radius:6px;margin-bottom:16px;background:#1f2937}
</style>
</head>
<body>
<div class="layout">
  <nav>
    <div class="brand">🛡️ WebShield</div>
    <a href="{{ url_for('dashboard') }}" class="{{ 'active' if active=='dashboard' else '' }}">Dashboard</a>
    <a href="{{ url_for('rules') }}" class="{{ 'active' if active=='rules' else '' }}">Rules</a>
    <a href="{{ url_for('add_rule') }}" class="{{ 'active' if active=='add' else '' }}">Add Rule</a>
    <a href="{{ url_for('logs') }}" class="{{ 'active' if active=='logs' else '' }}">Logs</a>
  </nav>
  <main>
    {% with messages = get_flashed_messages() %}
      {% if messages %}{% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}{% endif %}
    {% endwith %}
    {{ body|safe }}
  </main>
</div>
</body>
</html>
"""


def render(active, title, sub, body_html):
    return render_template_string(
        BASE_HTML, active=active, body=f"<h1>{title}</h1><div class='sub'>{sub}</div>{body_html}"
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def root():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    info = get_status()
    demo_banner = (
        '<div class="flash" style="background:#3a2f0b;color:#d29922">'
        'Demo mode — showing sample data, no live firewall is being controlled.'
        '</div>' if DEMO_MODE else ''
    )
    body = f"""
    {demo_banner}
    <div class="cards">
      <div class="card"><div class="label">Firewall Status</div>
        <div class="value ok">Active</div></div>
      <div class="card"><div class="label">Default INPUT Policy</div>
        <div class="value">{info['input_policy']}</div></div>
      <div class="card"><div class="label">Active Rules</div>
        <div class="value">{info['rule_count']}</div></div>
      <div class="card"><div class="label">Last Checked</div>
        <div class="value" style="font-size:16px">{datetime.now().strftime('%H:%M:%S')}</div></div>
    </div>
    <pre>{info['raw']}</pre>
    """
    return render("dashboard", "Dashboard", "Overview of firewall status and system information", body)


@app.route("/rules")
def rules():
    rules_out = get_rules()
    body = f"<pre>{rules_out}</pre>"
    return render("rules", "Active Rules", "Current iptables ruleset", body)


@app.route("/add", methods=["GET", "POST"])
def add_rule():
    if request.method == "POST":
        action = request.form.get("action")
        target_type = request.form.get("target_type")
        value = request.form.get("value", "").strip()
        proto = request.form.get("proto", "tcp")

        if target_type == "ip":
            cmd = "block-ip" if action == "block" else "unblock-ip"
            ok, out = run_firewall(cmd, value)
        else:
            cmd = "block-port" if action == "block" else "allow-port"
            ok, out = run_firewall(cmd, value, proto)

        flash(out.strip() or "Done.")
        return redirect(url_for("rules"))

    body = """
    <form class="inline" method="post">
      <select name="target_type">
        <option value="port">Port</option>
        <option value="ip">IP Address</option>
      </select>
      <select name="action">
        <option value="allow">Allow</option>
        <option value="block">Block</option>
      </select>
      <input name="value" placeholder="e.g. 8080 or 203.0.113.45" required>
      <select name="proto">
        <option value="tcp">TCP</option>
        <option value="udp">UDP</option>
      </select>
      <button type="submit">Apply Rule</button>
    </form>
    <p style="color:var(--muted);font-size:13px">
      Runs firewall.sh under the hood via sudo. The app must be started with
      permission to run it (see README for the sudoers snippet).
    </p>
    """
    return render("add", "Add Rule", "Allow or block a port / IP address", body)


@app.route("/logs")
def logs():
    entries = get_logs()
    rows = "".join(f"<tr><td>{e.strip()}</td></tr>" for e in entries) or \
           "<tr><td>No log entries yet.</td></tr>"
    body = f"<table><tr><th>Log Entry</th></tr>{rows}</table>"
    return render("logs", "Logs", f"Last {len(entries)} entries from {LOG_FILE}", body)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
