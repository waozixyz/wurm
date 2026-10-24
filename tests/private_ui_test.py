#!/usr/bin/env python3
"""Exercise only this test's app/window on its verified, private Xvfb server."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/research/ui"


def stop(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
                 "SESSION_MANAGER", "DESKTOP_AUTOSTART_ID"):
        env.pop(name, None)
    env.update(YUE_DESKTOP_RECOVERY="0", SDL_RENDER_DRIVER="software",
               SDL_FRAMEBUFFER_ACCELERATION="0", SDL_AUDIODRIVER="dummy", LP_NUM_THREADS="1", ZIRAN_PAR_THREADS="1")
    read_fd, write_fd = os.pipe()
    server = app = None
    try:
        server = subprocess.Popen(["Xvfb", "-displayfd", str(write_fd), "-screen", "0", "1000x720x24",
                                   "-nolisten", "tcp", "-noreset"], env=env, pass_fds=(write_fd,),
                                  stdout=subprocess.DEVNULL, stderr=open(OUT / "xvfb.log", "wb"), start_new_session=True)
        os.close(write_fd)
        if not select.select([read_fd], [], [], 10)[0]:
            raise RuntimeError("Private Xvfb did not provide a display")
        number = os.read(read_fd, 64).decode().strip()
        if not number.isdecimal() or server.poll() is not None:
            raise RuntimeError("Private Xvfb failed to create its own display socket")
        executable = Path(f"/proc/{server.pid}/exe").resolve()
        command = Path(f"/proc/{server.pid}/cmdline").read_bytes().split(b"\0")
        if executable != Path(shutil.which("Xvfb")).resolve() or b"-displayfd" not in command or server.poll() is not None:
            raise RuntimeError("Private X server identity mismatch")
        env["DISPLAY"] = ":" + number
        evidence = {"server_pid": server.pid, "server_executable": str(executable),
                    "server_command": [x.decode() for x in command if x], "display": env["DISPLAY"]}
        app = subprocess.Popen([str(ROOT / "build/Worm-desktop")], cwd=ROOT, env=env,
                               stdout=open(OUT / "app.log", "wb"), stderr=subprocess.STDOUT, start_new_session=True)
        window = None
        for attempt in range(100):
            if app.poll() is not None:
                raise RuntimeError(f"App exited with {app.returncode}")
            result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)], env=env,
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                window = result.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        if window is None:
            raise RuntimeError("No owned Worm window appeared")
        evidence.update(app_pid=app.pid, app_executable=str(Path(f"/proc/{app.pid}/exe").resolve()), window=window)

        def key(*keys):
            subprocess.run(["xdotool", "key", "--window", window, "--clearmodifiers", *keys], env=env, check=True)

        def capture(name):
            # Recheck the actual server before any pixel capture; never inherit a desktop.
            if server.poll() is not None or Path(f"/proc/{server.pid}/exe").resolve() != executable:
                raise RuntimeError("Owned capture source disappeared")
            subprocess.run(["import", "-display", env["DISPLAY"], "-window", window,
                            str(OUT / (name + ".png"))], env=env, check=True, timeout=15)

        time.sleep(0.35)
        capture("stages")
        # The game opens on the stages; Q from a paused level returns to that level's stage.
        # Only Garden is open, so Left/Right must keep it.
        for level, keys in ((1, ["Home"]), (11, ["q", "Home"] + ["Down"] * 10),
                            (33, ["q", "Right", "End"])):
            key(*keys)
            time.sleep(0.6)
            key("Return")
            time.sleep(0.3)
            key("space")
            time.sleep(0.15)
            capture(f"level-{level:02}")
        (OUT / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print("Private UI local test rendered the Garden stage and levels 1, 11, 33.")
    finally:
        os.close(read_fd)
        stop(app)
        stop(server)


if __name__ == "__main__":
    main()
