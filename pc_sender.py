import json
import time
import urllib.request
import urllib.error
import psutil
import serial

PORT = "/dev/cu.usbmodem1101"
BAUD = 115200
RECONNECT_DELAY = 2
GH_STATUS_URL = "https://githubstatus.com"

# Coordinates for weather (currently set to Detroit/SE Michigan)
LAT = 43.1230
LON = -86.1553
WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph"
)

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Mod. showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow shw",
    95: "Thunderstorm",
}

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

    except Exception as e:
        return ["Status check error", str(e)[:28], "Retrying soon..."]

def get_weather():
    try:
        req = urllib.request.Request(
            WEATHER_URL,
            headers={"User-Agent": "Badger2040-Dashboard"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        cur = data.get("current", {})
        temp = round(cur.get("temperature_2m", 0))
        feels = round(cur.get("apparent_temperature", 0))
        wind = round(cur.get("wind_speed_10m", 0))
        code = cur.get("weather_code", 0)
        cond = WMO_CODES.get(code, f"Code {code}")

        return [
            f"Temp: {temp}F (Feels {feels}F)",
            f"Cond: {cond}",
            f"Wind: {wind} mph",
            str(code),
        ]
    except Exception as e:
        return ["Weather error", str(e)[:28], "Retrying soon...", "-1"]


def connect_serial():
    while True:
        try:
            connection = serial.Serial(
                PORT, BAUD, timeout=1, write_timeout=1
            )
            time.sleep(2)
            print(f"Connected to badge on {PORT}")
            return connection
        except serial.SerialException as e:
            print(f"Unable to connect to badge on {PORT}: {e}; retrying")
            time.sleep(RECONNECT_DELAY)


def send_payload(connection, payload):
    encoded_payload = payload.encode("utf-8")
    while True:
        try:
            connection.write(encoded_payload)
            return connection
        except serial.SerialException as e:
            print(f"Badge connection lost: {e}; reconnecting")
            try:
                connection.close()
            except serial.SerialException as close_error:
                print(f"Error closing serial connection: {close_error}")
            time.sleep(RECONNECT_DELAY)
            connection = connect_serial()


def main():
    ser = connect_serial()
    while True:
        # Page 1: Mac System Stats
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        now = time.strftime("%I:%M %p")
        page1 = f"Time: {now}|CPU Load: {cpu}%|RAM Used: {ram}%"

        # Page 2: GitHub Status
        page2 = "|".join(get_github_status())

        # Page 3: Local Weather
        page3 = "|".join(get_weather())

        payload = f"{page1}||{page2}||{page3}\n"
        ser = send_payload(ser, payload)
        print("Sent:", payload.strip())

        time.sleep(30)


if __name__ == "__main__":
    main()
