import subprocess
import time

import serial


PORT = "/dev/cu.usbmodem1101"
BAUD = 115200
RECONNECT_DELAY = 2
SERIAL_TIMEOUT = 0.2
OSASCRIPT_TIMEOUT = 5

STATUS_SCRIPT = '''
if application "Music" is running then
    tell application "Music"
        if player state is stopped then
            return "Nothing playing" & tab & "" & tab & "stopped"
        end if
        set track_name to name of current track
        set track_artist to artist of current track
        set playback_state to player state as text
        return track_name & tab & track_artist & tab & playback_state
    end tell
else
    return "Music is not running" & tab & "" & tab & "stopped"
end if
'''

CONTROL_SCRIPTS = {
    "MEDIA:PREVIOUS": 'tell application "Music" to previous track',
    "MEDIA:PLAY_PAUSE": 'tell application "Music" to playpause',
    "MEDIA:NEXT": 'tell application "Music" to next track',
    "MEDIA:VOLUME_UP": '''
set currentVolume to output volume of (get volume settings)
set targetVolume to currentVolume + 10
if targetVolume > 100 then set targetVolume to 100
set volume output volume targetVolume
''',
    "MEDIA:VOLUME_DOWN": '''
set currentVolume to output volume of (get volume settings)
set targetVolume to currentVolume - 10
if targetVolume < 0 then set targetVolume to 0
set volume output volume targetVolume
''',
}


def run_osascript(script):
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=OSASCRIPT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("osascript timed out") from error
    if result.returncode:
        details = result.stderr.strip()
        raise RuntimeError(details or f"osascript exited with status {result.returncode}")
    return result.stdout.strip()


def clean_field(value):
    return " ".join(value.replace("|", " ").replace("\t", " ").split())


def get_music_status():
    fields = run_osascript(STATUS_SCRIPT).split("\t", 2)
    if len(fields) != 3:
        raise RuntimeError("Unexpected Apple Music status response")
    return tuple(clean_field(field) for field in fields)


def send_status(connection):
    try:
        track, artist, state = get_music_status()
    except RuntimeError as error:
        print(f"Apple Music status unavailable: {error}")
        track, artist, state = "Apple Music unavailable", "", "Check Mac"

    message = "MEDIA|{}|{}|{}\n".format(track, artist, state)
    connection.write(message.encode("utf-8"))


def handle_command(connection, command):
    if command == "MEDIA:GET":
        send_status(connection)
    elif command in CONTROL_SCRIPTS:
        try:
            run_osascript(CONTROL_SCRIPTS[command])
        except RuntimeError as error:
            print(f"Apple Music command failed: {error}")
        send_status(connection)


def connect_serial():
    while True:
        try:
            connection = serial.Serial(
                PORT,
                BAUD,
                timeout=SERIAL_TIMEOUT,
                write_timeout=1,
            )
        except serial.SerialException as error:
            print(f"Unable to connect to badge on {PORT}: {error}; retrying")
            time.sleep(RECONNECT_DELAY)
            continue

        time.sleep(2)
        print(f"Connected to badge on {PORT}")
        return connection


def serve():
    connection = connect_serial()
    try:
        while True:
            try:
                command = connection.readline().decode("utf-8").strip()
                if command:
                    handle_command(connection, command)
            except UnicodeDecodeError as error:
                print(f"Ignoring invalid badge message: {error}")
            except serial.SerialException as error:
                print(f"Badge connection lost: {error}; reconnecting")
                try:
                    connection.close()
                except serial.SerialException as close_error:
                    print(f"Error closing serial connection: {close_error}")
                time.sleep(RECONNECT_DELAY)
                connection = connect_serial()
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print("\nStopped media sender.")
