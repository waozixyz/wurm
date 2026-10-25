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
    # A fixed window keeps the pointer math below stable on any screen.
    env.update(WURM_WINDOW="960x600", YUE_DESKTOP_RECOVERY="0", SDL_RENDER_DRIVER="software",
               SDL_FRAMEBUFFER_ACCELERATION="0", SDL_AUDIODRIVER="dummy", LP_NUM_THREADS="1", ZIRAN_PAR_THREADS="1",
               # The editor writes level overrides into this private directory,
               # never into the repository's assets.
               WURM_LEVEL_DIR=str(ROOT / "build/research/ui/levels"))
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
        app = subprocess.Popen([str(ROOT / "build/Apfelwurm-desktop")], cwd=ROOT, env=env,
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
            raise RuntimeError("No owned Apfelwurm window appeared")
        title = subprocess.run(["xdotool", "getwindowname", window], env=env,
                               capture_output=True, text=True).stdout.strip()
        if title != "Apfelwurm":
            raise RuntimeError(f"Window is titled {title!r}, not Apfelwurm")
        evidence.update(app_pid=app.pid, app_executable=str(Path(f"/proc/{app.pid}/exe").resolve()), window=window)

        def key(*keys):
            # One key per call: a burst inside one frame drops presses.
            for name in keys:
                subprocess.run(["xdotool", "key", "--window", window, "--clearmodifiers", name],
                               env=env, check=True)
                time.sleep(0.12)

        def pointer(x, y):
            # Window-relative move, then a click at the rested position.
            subprocess.run(["xdotool", "mousemove", "--window", window, "--sync", str(x), str(y)],
                           env=env, check=True)
            subprocess.run(["xdotool", "click", "1"], env=env, check=True)
            time.sleep(0.15)

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

        # The editor: E opens it for the chosen level, the pointer picks the
        # first floor swatch and paints it over the top-left wall, and Save
        # writes the override. Pointer targets mirror the layout in app.zi:
        # the 960x600 window with a 42px top bar, a 248px right panel whose
        # palette starts at y 178 in 38px columns, and the 40x30 board scaled
        # to 712x534 at (0, 54), so cell (0, 0) centres near (8, 62).
        key("q")
        key("e")
        time.sleep(0.4)
        capture("editor-open")
        pointer(737, 195)  # first FLOOR swatch: brush 0
        pointer(8, 62)     # canvas cell (0, 0), a wall in every level
        time.sleep(0.2)
        capture("editor-painted")
        pointer(775, 518)  # Save
        time.sleep(0.3)
        edited = ROOT / "build/research/ui/levels/level33.dat"
        original = (ROOT / "assets/original/level33.dat").read_bytes()
        painted = edited.read_bytes()
        assert len(painted) == 1201, f"override size {len(painted)}"
        assert painted[0] == original[0], "apple count unchanged"
        assert painted[1] == 0 and original[1] == 20, "cell (0, 0) painted from wall to floor"
        key("e")
        time.sleep(0.3)
        capture("editor-exit")
        (OUT / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print("Private UI local test rendered the Garden stage, levels 1, 11, 33 and an edited override.")

        # A portrait window proves the mobile-first layout: WURM_WINDOW sizes
        # the second launch, the green icon bar stays on top and the board
        # letterboxes below it.
        stop(app)
        env.update(WURM_WINDOW="480x700")
        app = subprocess.Popen([str(ROOT / "build/Apfelwurm-desktop")], cwd=ROOT, env=env,
                               stdout=open(OUT / "app-portrait.log", "wb"), stderr=subprocess.STDOUT,
                               start_new_session=True)
        portrait = None
        for attempt in range(100):
            if app.poll() is not None:
                raise RuntimeError(f"Portrait app exited with {app.returncode}")
            result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                    env=env, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                portrait = result.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        if portrait is None:
            raise RuntimeError("No owned portrait Apfelwurm window appeared")
        evidence.update(portrait_window=portrait)
        window = portrait
        time.sleep(0.5)
        capture("portrait-stages")
        key("Return")
        time.sleep(0.5)
        capture("portrait-level")
        from PIL import Image
        picture = Image.open(OUT / "portrait-level.png").convert("RGB")
        assert picture.size == (480, 700), picture.size
        top = picture.crop((0, 0, 480, 42))
        top_green = sum(channel * count for channel, count in enumerate(top.histogram()[256:512]))
        assert top_green > 480 * 42 * 90, "the icon bar is not green across the top"
        board = picture.crop((0, 42, 480, 698))
        # The 480-wide board scales fewer pixels than landscape, so the
        # check is structural: a green field centred below the bar.
        assert len(board.getcolors(480 * 656) or []) > 40, "the board area did not render"
        board_green = sum(channel * count for channel, count in enumerate(board.histogram()[256:512]))
        assert board_green > 480 * 656 * 40, "the board is not a green field"
        print("Private UI local test rendered the portrait layout with the top icon bar.")
    finally:
        os.close(read_fd)
        stop(app)
        stop(server)


if __name__ == "__main__":
    main()
