'''
Usage:
  python3 monitor.py            
  TEST_MODE=1 python3 monitor.py (no SSH required)
'''
import os
import json
import random
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

TEST_MODE = bool(int(os.environ.get("TEST_MODE", "0")))


SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "your_email@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "your_app_password")
EMAIL_TO = os.environ.get("EMAIL_TO", "you@example.com")

DISK_THRESHOLD = float(os.environ.get("DISK_THRESHOLD", "90"))
MEM_THRESHOLD = float(os.environ.get("MEM_THRESHOLD", "85"))

HOSTS_FILE = os.environ.get("HOSTS_FILE", "hosts.json")
SSH_TIMEOUT = float(os.environ.get("SSH_TIMEOUT", "8"))



try:
    import paramiko
except Exception:
    paramiko = None


def load_hosts(path: str = HOSTS_FILE) -> List[Dict]:
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("servers", [])


def simulate_host(name: str) -> Dict:
    """Generate fake stats for demo/testing."""
    disk = random.uniform(10, 98)
    mem = random.uniform(10, 95)
    load = random.uniform(0.1, 3.0)
    return {
        "name": name,
        "disk_percent": round(disk, 1),
        "memory_percent": round(mem, 1),
        "load_avg": round(load, 2),
        "error": None,
    }


def ssh_check(host: Dict) -> Dict:
    """Run remote commands via SSH. Expects host dict with host,user,key_file or password.
    If paramiko is not available or connection fails, returns an error inside the dict.
    """
    result = {"name": host.get("name", host.get("host")), "error": None}

    if paramiko is None:
        result.update({"disk_percent": -1, "memory_percent": -1, "load_avg": -1,
                       "error": "paramiko not installed"})
        return result

    hostname = host.get("host")
    user = host.get("user")
    key_file = host.get("key_file")
    password = host.get("password")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if key_file:
            client.connect(hostname, username=user, key_filename=key_file, timeout=SSH_TIMEOUT)
        else:
            client.connect(hostname, username=user, password=password, timeout=SSH_TIMEOUT)

        # Disk percent for root
        stdin, stdout, stderr = client.exec_command("df -h / | awk 'NR==2 {print $5}'")
        disk_raw = stdout.read().decode().strip()

        stdin, stdout, stderr = client.exec_command("free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2 }'")
        mem_raw = stdout.read().decode().strip()

        stdin, stdout, stderr = client.exec_command("uptime | awk -F'load average:' '{ print $2 }' | cut -d',' -f1")
        load_raw = stdout.read().decode().strip()

        # Parsing
        try:
            disk_percent = float(disk_raw.replace('%', '').strip())
        except Exception:
            disk_percent = -1
        try:
            memory_percent = float(mem_raw)
        except Exception:
            memory_percent = -1
        try:
            load_avg = float(load_raw.strip())
        except Exception:
            load_avg = -1

        result.update({
            "disk_percent": disk_percent,
            "memory_percent": memory_percent,
            "load_avg": load_avg,
            "error": None,
        })
        client.close()
    except Exception as e:
        result.update({"disk_percent": -1, "memory_percent": -1, "load_avg": -1, "error": str(e)})

    return result


def check_hosts(hosts: List[Dict]) -> List[Dict]:
    results = []
    for h in hosts:
        name = h.get("name") or h.get("host")
        if TEST_MODE:
            r = simulate_host(name)
        else:
            r = ssh_check(h)
        results.append(r)
    return results


def build_report(results: List[Dict]) -> (str, bool):
    lines = []
    any_alert = False
    for r in results:
        lines.append(f"[{r.get('name')}]")
        if r.get("error"):
            lines.append(f"  ERROR: {r.get('error')}")
            any_alert = True
        else:
            lines.append(f"  Disk: {r.get('disk_percent')}%")
            lines.append(f"  Memory: {r.get('memory_percent')}%")
            lines.append(f"  Load: {r.get('load_avg')}")

            if r.get("disk_percent", -1) >= DISK_THRESHOLD:
                lines.append(f"  -> ALERT: Disk >= {DISK_THRESHOLD}%")
                any_alert = True
            if r.get("memory_percent", -1) >= MEM_THRESHOLD:
                lines.append(f"  -> ALERT: Memory >= {MEM_THRESHOLD}%")
                any_alert = True

        lines.append("")
    body = "\n".join(lines)
    return body, any_alert


def send_email(subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print('Email send failed:', e)
        return False


def main():
    print('TEST_MODE=', TEST_MODE)
    hosts = load_hosts()
    results = check_hosts(hosts)
    report, any_alert = build_report(results)

    print('\n----- REPORT -----\n')
    print(report)

    if any_alert:
        subj = f"ALERT: Remote Monitor - issues detected"
        ok = send_email(subj, report)
        print('Email sent:', ok)
    else:
        print('No alerts. No email sent by default.')


if __name__ == '__main__':
    main()
