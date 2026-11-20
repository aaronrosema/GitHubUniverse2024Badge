from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PRELOAD = ROOT / "preload"
POLL_INTERVAL = 1
RETRY_INTERVAL = 5
MPREMOTE_TIMEOUT = 15


def _run_mpremote(port, *args, check=True):
    command = [sys.executable, "-m", "mpremote", "connect", port, *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=MPREMOTE_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"mpremote {' '.join(args)} timed out after {MPREMOTE_TIMEOUT} seconds"
        ) from error
    if check and result.returncode:
        details = (result.stdout + result.stderr).strip()
        raise RuntimeError(details or f"mpremote exited with status {result.returncode}")
    return result


def _find_badger():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mpremote", "connect", "list"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=MPREMOTE_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"mpremote device discovery timed out after {MPREMOTE_TIMEOUT} seconds"
        ) from error
    if result.returncode:
        details = (result.stdout + result.stderr).strip()
        raise RuntimeError(details or f"mpremote exited with status {result.returncode}")

    ports = [
        line.split(maxsplit=1)[0]
        for line in result.stdout.splitlines()
        if "micropython" in line.lower()
    ]
    if len(ports) > 1:
        raise RuntimeError(f"Found multiple MicroPython devices: {', '.join(ports)}")
    return ports[0] if ports else None


def _snapshot():
    return {
        path.relative_to(PRELOAD).as_posix(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in PRELOAD.rglob("*")
        if path.is_file()
    }


def _deploy(port, files, removed=()):
    directories = sorted(
        {Path(filename).parent for filename in files if Path(filename).parent != Path(".")},
        key=lambda path: (len(path.parts), path.as_posix()),
    )
    for directory in directories:
        remote_dir = f":/{directory.as_posix()}"
        result = _run_mpremote(port, "mkdir", remote_dir, check=False)
        if result.returncode:
            details = (result.stdout + result.stderr).strip()
            if "EEXIST" not in details and "File exists" not in details:
                raise RuntimeError(details or f"Could not create {remote_dir}")

    files_by_directory = {}
    for filename in files:
        directory = Path(filename).parent
        files_by_directory.setdefault(directory, []).append(filename)

    for directory, filenames in sorted(
        files_by_directory.items(), key=lambda item: item[0].as_posix()
    ):
        remote_dir = ":/" if directory == Path(".") else f":/{directory.as_posix()}/"
        local_paths = [str(PRELOAD / filename) for filename in sorted(filenames)]
        _run_mpremote(port, "cp", *local_paths, remote_dir)

    for filename in removed:
        result = _run_mpremote(port, "rm", f":/{filename}", check=False)
        if result.returncode:
            details = (result.stdout + result.stderr).strip()
            if "ENOENT" not in details and "No such file" not in details:
                raise RuntimeError(details or f"Could not remove /{filename}")

    _run_mpremote(port, "reset")


def watch():
    print(f"Watching {PRELOAD.relative_to(ROOT)} for a connected Badger. Press Ctrl-C to stop.")
    synced_by_port = {}
    active_port = None
    retry_after = 0

    while True:
        try:
            port = _find_badger()
        except RuntimeError as error:
            print(f"Device detection error: {error}")
            time.sleep(POLL_INTERVAL)
            continue

        if port != active_port:
            active_port = port
            retry_after = 0
            if port:
                print(f"Found Badger on {port}")
                synced_by_port.setdefault(port, {})
            else:
                print("Badger disconnected; waiting for connection.")

        if port:
            snapshot = _snapshot()
            synced = synced_by_port[port]
            changed = [name for name, state in snapshot.items() if synced.get(name) != state]
            removed = [name for name in synced if name not in snapshot]
            now = time.monotonic()
            if (changed or removed) and now >= retry_after:
                try:
                    print(
                        f"Syncing {len(changed)} changed and {len(removed)} removed file(s)..."
                    )
                    _deploy(port, changed, removed)
                    for name in removed:
                        synced.pop(name, None)
                    synced.update({name: snapshot[name] for name in changed})
                    print("Sync complete; device reset.")
                    retry_after = 0
                except RuntimeError as error:
                    print(f"Deployment failed: {error}")
                    retry_after = time.monotonic() + RETRY_INTERVAL

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        watch()
    except KeyboardInterrupt:
        print("\nStopped watching.")
