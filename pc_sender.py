import json
import time
import urllib.request
import psutil
import serial

PORT = "/dev/cu.usbmodem1101"
BAUD = 115200
GH_STATUS_URL = "https://githubstatus.com"

import json
import time
import urllib.request
import urllib.error
import psutil
import serial

PORT = "/dev/cu.usbmodem1101"
BAUD = 115200
GH_STATUS_URL = "https://githubstatus.com"

def get_github_status():
    try:
        req = urllib.request.Request(
            GH_STATUS_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8").strip()
            if not raw:
                return ["Status check error", "Empty response", "Retrying soon..."]
            data = json.loads(raw)

        impacted = [
            f"{c['name']}: {c['status'].replace('_', ' ')}"
            for c in data.get("components", [])
            if c.get("status") != "operational"
            and "githubstatus.com" not in c.get("name", "").lower()
        ]

        if not impacted:
            return ["All systems good!", "All GitHub services", "operational"]
        return impacted[:3]

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return ["Status HTTP Error", f"Code: {e.code}", "Retrying soon..."]
    except Exception as e:
        print(f"GitHub status error: {e}")
        return ["Status check error", str(e)[:28], "Retrying soon..."]

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

while True:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    now = time.strftime("%I:%M %p")
    page1 = f"Time: {now}|CPU Load: {cpu}%|RAM Used: {ram}%"

    gh_lines = get_github_status()
    page2 = "|".join(gh_lines)

    payload = f"{page1}||{page2}\n"
    ser.write(payload.encode("utf-8"))
    print("Sent:", payload.strip())

    time.sleep(30)


while True:
    # Page 1: Mac System Stats
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    now = time.strftime("%I:%M %p")
    page1 = f"Time: {now}|CPU Load: {cpu}%|RAM Used: {ram}%"

    # Page 2: GitHub Status
    gh_lines = get_github_status()
    page2 = "|".join(gh_lines)

    # Send both pages separated by '||'
    payload = f"{page1}||{page2}\n"
    ser.write(payload.encode("utf-8"))

    time.sleep(30)
