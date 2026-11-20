import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path


LABEL = "com.badgerbodger.sender"
ROOT = Path(__file__).resolve().parents[1]
SERVICE_SCRIPT = Path(__file__).resolve().with_name("badge_sender_service.py")
AGENT_DIRECTORY = Path.home() / "Library" / "LaunchAgents"
AGENT_PATH = AGENT_DIRECTORY / f"{LABEL}.plist"
LOG_DIRECTORY = Path.home() / "Library" / "Logs" / "BadgerBodger"


def agent_configuration():
    return {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(SERVICE_SCRIPT)],
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "ThrottleInterval": 10,
        "EnvironmentVariables": {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONUNBUFFERED": "1",
        },
        "StandardOutPath": str(LOG_DIRECTORY / "sender.log"),
        "StandardErrorPath": str(LOG_DIRECTORY / "sender.log"),
    }


def run_launchctl(*arguments):
    result = subprocess.run(
        ["/bin/launchctl", *arguments],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        details = (result.stdout + result.stderr).strip()
        raise RuntimeError(details or f"launchctl {' '.join(arguments)} failed")


def bootout_if_loaded():
    service_target = f"gui/{os.getuid()}/{LABEL}"
    try:
        run_launchctl("print", service_target)
    except RuntimeError as error:
        if "Could not find service" in str(error):
            return
        raise
    run_launchctl("bootout", service_target)


def stop_agent():
    if sys.platform != "darwin":
        raise RuntimeError("The badge sender LaunchAgent requires macOS")
    if not AGENT_PATH.is_file():
        raise RuntimeError("The badge sender LaunchAgent is not installed")
    bootout_if_loaded()


def start_agent():
    if sys.platform != "darwin":
        raise RuntimeError("The badge sender LaunchAgent requires macOS")
    if not AGENT_PATH.is_file():
        raise RuntimeError("The badge sender LaunchAgent is not installed")
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    run_launchctl("bootstrap", f"gui/{os.getuid()}", str(AGENT_PATH))


def install():
    if sys.platform != "darwin":
        raise RuntimeError("The badge sender LaunchAgent requires macOS")
    if not SERVICE_SCRIPT.is_file():
        raise RuntimeError(f"Sender service not found: {SERVICE_SCRIPT}")

    AGENT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    bootout_if_loaded()
    with AGENT_PATH.open("wb") as agent_file:
        plistlib.dump(agent_configuration(), agent_file)
    AGENT_PATH.chmod(0o644)
    start_agent()
    print(f"Installed and started {LABEL}")
    print(f"Logs: {LOG_DIRECTORY / 'sender.log'}")


def uninstall():
    if sys.platform != "darwin":
        raise RuntimeError("The badge sender LaunchAgent requires macOS")
    bootout_if_loaded()
    if AGENT_PATH.exists():
        AGENT_PATH.unlink()
    print(f"Removed {LABEL}")


def main():
    parser = argparse.ArgumentParser(description="Install the Badger Bodger LaunchAgent")
    parser.add_argument(
        "action",
        nargs="?",
        choices=("install", "uninstall"),
        default="install",
    )
    action = parser.parse_args().action
    if action == "install":
        install()
    else:
        uninstall()


if __name__ == "__main__":
    main()
