import queue
import threading
import time
from pathlib import Path
import sys

import psutil
import serial


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from media_sender import handle_command
from pc_sender import (
    BAUD,
    PORT,
    RECONNECT_DELAY,
    get_github_status,
    get_weather,
)


SERIAL_TIMEOUT = 0.2
DASHBOARD_INTERVAL = 30


def build_dashboard_payload():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    now = time.strftime("%I:%M %p")
    page1 = f"Time: {now}|CPU Load: {cpu}%|RAM Used: {ram}%"
    page2 = "|".join(get_github_status())
    page3 = "|".join(get_weather())
    return f"{page1}||{page2}||{page3}\n"


def connect_serial():
    last_notice = 0
    while True:
        try:
            connection = serial.Serial(
                PORT,
                BAUD,
                timeout=SERIAL_TIMEOUT,
                write_timeout=1,
            )
        except serial.SerialException as error:
            now = time.monotonic()
            if now - last_notice >= 30:
                print(f"Waiting for badge on {PORT}: {error}")
                last_notice = now
            time.sleep(RECONNECT_DELAY)
            continue

        time.sleep(2)
        print(f"Connected to badge on {PORT}")
        return connection


def reconnect(connection, reason):
    print(f"Badge connection lost: {reason}; reconnecting")
    try:
        connection.close()
    except serial.SerialException as error:
        print(f"Error closing serial connection: {error}")
    time.sleep(RECONNECT_DELAY)
    return connect_serial()


def update_dashboard_in_background(results):
    results.put(build_dashboard_payload())


def serve():
    connection = connect_serial()
    dashboard_results = queue.Queue(maxsize=1)
    dashboard_worker = None
    next_dashboard_update = 0

    while True:
        if not Path(PORT).exists():
            connection = reconnect(connection, f"{PORT} was removed")
            continue

        now = time.monotonic()
        if dashboard_worker is None and now >= next_dashboard_update:
            dashboard_worker = threading.Thread(
                target=update_dashboard_in_background,
                args=(dashboard_results,),
                daemon=True,
            )
            dashboard_worker.start()
            next_dashboard_update = now + DASHBOARD_INTERVAL

        try:
            if dashboard_worker is not None and not dashboard_worker.is_alive():
                try:
                    payload = dashboard_results.get_nowait()
                except queue.Empty:
                    print("Dashboard refresh did not produce data")
                else:
                    connection.write(payload.encode("utf-8"))
                    print("Sent dashboard update")
                dashboard_worker = None

            message = connection.readline()
            if message:
                command = message.decode("utf-8").strip()
                if command:
                    handle_command(connection, command)
        except UnicodeDecodeError as error:
            print(f"Ignoring invalid badge message: {error}")
        except serial.SerialException as error:
            connection = reconnect(connection, str(error))


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print("\nStopped badge sender service.")
