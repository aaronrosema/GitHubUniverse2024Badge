import subprocess
import sys
from pathlib import Path

from install_launch_agent import AGENT_PATH, start_agent, stop_agent


ROOT = Path(__file__).resolve().parents[1]
WATCHER = Path(__file__).resolve().with_name("watch_badger.py")


def sync_badge():
    if not AGENT_PATH.is_file():
        raise RuntimeError("Install the badge sender LaunchAgent before syncing")

    stop_agent()
    try:
        result = subprocess.run(
            [sys.executable, str(WATCHER), "--once"],
            cwd=ROOT,
            check=False,
        )
    finally:
        start_agent()

    if result.returncode:
        raise RuntimeError(f"Badge sync failed with exit status {result.returncode}")


if __name__ == "__main__":
    try:
        sync_badge()
    except KeyboardInterrupt:
        print("\nSync interrupted; restarting the badge sender.")
