#!/usr/bin/env python3
"""Exercise only this test's app/window on its verified, private Xvfb server."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/research/ui"
DESKTOP = Path(os.environ.get("WURM_TEST_BINARY", ROOT / "build/Apfelwurm-desktop"))


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
    level_directory = Path(tempfile.mkdtemp(prefix="levels-", dir=OUT))
    env = dict(os.environ)
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
                 "SESSION_MANAGER", "DESKTOP_AUTOSTART_ID"):
        env.pop(name, None)
    # A fixed window keeps the pointer math below stable on any screen.
    env.update(WURM_WINDOW="960x600", YUE_DESKTOP_RECOVERY="0", SDL_RENDER_DRIVER="software",
               SDL_FRAMEBUFFER_ACCELERATION="0", SDL_AUDIODRIVER="dummy", LP_NUM_THREADS="1", ZIRAN_PAR_THREADS="1",
               # The editor writes level overrides into this private directory,
               # never into the repository's assets.
               WURM_LEVEL_DIR=str(level_directory))
    env["WURM_PROBE_SCENE"] = "0"
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
        app = subprocess.Popen([str(DESKTOP)], cwd=ROOT / "build", env=env,
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
        from PIL import Image
        import numpy
        title_pixels = numpy.asarray(Image.open(OUT / "stages.png").convert("RGB"))
        assert ((title_pixels.max(axis=2) > 40).mean()) > 0.95, "title artwork is missing or black"
        # Launch from build/, as the actual desktop launcher does, then use
        # the single Play button. Q from a paused level returns to the title.
        pointer(480, 530)
        time.sleep(0.15)
        capture("controls-choice")
        pointer(340, 428)
        assert (level_directory / "controls.dat").read_bytes() == bytes([0]), "swipe choice was not persisted"
        # The choice goes straight into level 1: no stage or level menu.
        time.sleep(0.2)
        key("space")
        time.sleep(0.15)
        capture("level-01")
        key("q")
        time.sleep(0.4)

        # Arrow keys no longer page to another menu. The editor remains
        # accessible through its existing desktop shortcut, outside Play.
        key("Right")
        time.sleep(0.4)
        capture("title-no-pages")
        returned = numpy.asarray(Image.open(OUT / "title-no-pages.png").convert("RGB"))
        assert numpy.array_equal(returned[:450], title_pixels[:450]), "title unexpectedly changed pages"
        key("e")
        time.sleep(0.3)
        capture("editor-browser")
        from PIL import Image
        import numpy
        browser = numpy.asarray(Image.open(OUT / "editor-browser.png").convert("RGB"), dtype=int)
        # The editor browser shares the softer dark garden surface.
        dark = float(((browser[:, :, 0] < 100) & (browser[:, :, 1] < 120)).mean())
        assert dark > 0.5, f"browser surface is only {dark:.0%} dark"

        # All five landscapes are reachable from the same editor browser.
        for chapter in ('leafwood', 'pinewood', 'lake', 'mountains', 'meadow'):
            pointer(930, 68)
            time.sleep(.15)
            capture('browser-' + chapter)

        # Card 14 of the forty-level Meadow browser, laid out with the same column search as
        # DrawLevelBrowser for the 960x600 window.
        area_w, area_h = 960, 558
        columns = next(c for c in range(4, 12)
                       if -(-40 // c) * (((area_w - 16 - (c - 1) * 8) / c) * 0.75 + 30)
                       + ((-(-40 // c)) - 1) * 8 + 56 <= area_h)
        item_w = (area_w - 16 - (columns - 1) * 8) / columns
        item_h = item_w * 0.75 + 30
        index = 13
        card_x = 8 + (index % columns) * (item_w + 8) + item_w / 2
        card_y = 42 + 56 + (index // columns) * (item_h + 8) + item_h / 2
        pointer(int(card_x), int(card_y))
        time.sleep(0.3)
        capture("editor-open")

        # The editor canvas on the chosen level: the pointer picks the
        # first floor swatch and paints it over the top-left wall, and Save
        # writes the override. Targets mirror the layout in app.zi: the
        # 960x600 window with a 42px top bar, a 248px right panel whose
        # palette starts at y 178 in 38px columns, and the 40x30 board
        # scaled to 712x534 at (0, 54), so cell (0, 0) centres near (8, 62).
        pointer(737, 195)  # first FLOOR swatch: brush 0
        pointer(8, 62)     # canvas cell (0, 0), a wall in every level
        time.sleep(0.2)
        capture("editor-painted")
        pointer(775, 518)  # Save
        time.sleep(0.3)
        edited = level_directory / "level14.dat"
        original = (ROOT / "build/designed/level14.dat").read_bytes()
        painted = edited.read_bytes()
        assert len(painted) == 2401, f"override size {len(painted)}"
        assert painted[0] == original[0], "apple count unchanged"
        assert painted[1] == 0 and original[1] == 20, "cell (0, 0) painted from wall to floor"

        # T stands the level up as portrait plays it: the canvas board
        # becomes tall, with dark bars beside it inside the canvas area.
        key("t")
        time.sleep(0.3)
        capture("editor-turned")
        turned = numpy.asarray(Image.open(OUT / "editor-turned.png").convert("RGB"), dtype=int)
        side_columns = ((turned[100:500, 0:712, 0] < 100) & (turned[100:500, 0:712, 1] < 120)).mean(axis=0)
        assert (side_columns > 0.9).sum() > 100, "the canvas board did not stand up"
        pointer(813, 269)  # Stone brush.
        pointer(223, 537)  # Portrait cell (5, 35), beyond landscape rows.
        pointer(775, 518)  # Save just this orientation.
        portrait_edit = level_directory / "level14-portrait.dat"
        assert portrait_edit.read_bytes()[1 + 5 * 40 + 35] == 21, "portrait lower-row edit was not saved"
        assert edited.read_bytes() == painted, "portrait save changed the landscape"
        pointer(156, 20)  # Landscape mode.
        capture("editor-landscape-independent")
        pointer(255, 20)  # Portrait mode.
        key("Tab", "space")
        capture("portrait-playtest")
        key("q")
        pointer(156, 20)
        key("e")
        time.sleep(0.3)
        capture("editor-exit")
        (OUT / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print("Private UI local test played the standing level, opened the editor with E, browsed the Meadow levels and edited one.")

        # A portrait window proves the mobile-first layout: WURM_WINDOW sizes
        # the second launch, the themed status bar stays on top and the board
        # letterboxes below it.
        stop(app)
        env.update(WURM_WINDOW="480x700")
        app = subprocess.Popen([str(DESKTOP)], cwd=ROOT / "build", env=env,
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
        portrait_title = numpy.asarray(Image.open(OUT / "portrait-stages.png").convert("RGB"))
        assert ((portrait_title.max(axis=2) > 40).mean()) > 0.95, "portrait title artwork is missing"
        key("Return")
        time.sleep(0.2)
        capture("portrait-level")
        from PIL import Image
        picture = Image.open(OUT / "portrait-level.png").convert("RGB")
        assert picture.size == (480, 700), picture.size
        top = picture.crop((0, 0, 480, 42))
        top_green = sum(channel * count for channel, count in enumerate(top.histogram()[256:512]))
        assert 480 * 42 * 40 < top_green < 480 * 42 * 130, "the themed status bar did not render across the top"
        board = picture.crop((0, 42, 480, 698))
        # The turned board fills the portrait width edge to edge: a green
        # field taller than wide with no black bars at the sides.
        assert len(board.getcolors(480 * 656) or []) > 40, "the board area did not render"
        board_green = sum(channel * count for channel, count in enumerate(board.histogram()[256:512]))
        assert board_green > 480 * 656 * 40, "the board is not a green field"
        black_columns = 0
        for column in range(picture.width):
            strip = picture.crop((column, 100, column + 1, 600))
            if max(strip.histogram()[0:256]) + max(strip.histogram()[512:768]) > 4800:
                black_columns += 1
        assert black_columns == 0, f"{black_columns} black side columns; the board did not turn"
        print("Private UI local test rendered the turned portrait board and the top icon bar.")

        # Real frame transitions save the next level immediately, including
        # a landscape boundary, and keep editor playtests out of progress.
        stop(app)
        probe_directory = level_directory / "progress-probe"
        probe_directory.mkdir()
        subprocess.run([str(ROOT / "build/Apfelwurm-modal-test")], cwd=ROOT,
                       env={**env, "WURM_LEVEL_DIR": str(probe_directory), "WURM_PROBE_PROGRESS": "1"},
                       check=True, timeout=30)

        # Each dialog is exercised in a narrow phone portrait and a short
        # phone landscape window. The probe is a separate, uninstalled host.
        for width, height in ((320, 568), (640, 360)):
            for mode, label in ((2, "paused"), (3, "game-over"), (5, "complete")):
                stop(app)
                name = f"{width}x{height}-{label}"
                log = OUT / (name + ".log")
                if mode == 3:
                    (level_directory / "run.dat").write_bytes(bytes([0, 3, 0, 0, 0, 0]))
                    (level_directory / "unlocked.dat").write_bytes(bytes([57]))
                env.update(WURM_PROBE_WIDTH=str(width), WURM_PROBE_HEIGHT=str(height), WURM_PROBE_MODE=str(mode))
                app = subprocess.Popen([str(ROOT / "build/Apfelwurm-modal-test")], cwd=ROOT, env=env,
                                       stdout=open(log, "wb"), stderr=subprocess.STDOUT, start_new_session=True)
                for attempt in range(100):
                    if app.poll() is not None:
                        raise RuntimeError(f"{name} exited with {app.returncode}: {log.read_text()[-1000:]}")
                    result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                            env=env, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        window = result.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                else:
                    raise RuntimeError("No owned dialog probe window")
                time.sleep(.4)
                capture(name)
                picture = Image.open(OUT / (name + ".png")).convert("RGB")
                assert picture.size == (width, height), name
                # Both full-width actions must fit entirely inside the window.
                compact = height < 400
                card_height = (252 if compact else 292) if mode == 2 else (288 if compact else 340)
                if mode == 2:
                    card_height += 56
                card_top = (height - card_height) / 2
                primary_y = round(card_top + card_height - (152 if mode == 2 else 96))
                secondary_y = round(card_top + card_height - 36)
                assert 24 < primary_y < secondary_y < height - 24, name
                # Exercise each primary action and require a real state change.
                pointer(width // 2, primary_y)
                for attempt in range(30):
                    if "mode=1" in log.read_text():
                        break
                    time.sleep(.05)
                else:
                    raise AssertionError(name + " primary action did not start/resume play")
                if mode == 3:
                    assert "mode=1 lives=3 level=57 score=0" in log.read_text(), "Try again did not use the furthest unlocked level"
                key("space")
                time.sleep(.15)
                # Reopened pause uses the pause card, including after game over.
                pause_height = (252 if compact else 292) + 56
                pointer(width // 2, round((height + pause_height) / 2 - 36))
                for attempt in range(30):
                    if "mode=0" in log.read_text():
                        break
                    time.sleep(.05)
                else:
                    raise AssertionError(name + " Back to title action failed")
        print("Private UI local test: all three dialogs fit portrait/landscape; all primary and title actions worked.")
        for width, height in ((320, 568), (360, 800), (800, 360)):
            stop(app)
            # A previous-version save unlocks its reached level on relaunch.
            (level_directory / "run.dat").write_bytes(bytes([57, 6, 120, 0, 0, 0]))
            (level_directory / "unlocked.dat").unlink(missing_ok=True)
            env.update(WURM_WINDOW=f"{width}x{height}")
            app = subprocess.Popen([str(DESKTOP)], cwd=ROOT / "build", env=env,
                                   stdout=open(OUT / f"title-{width}x{height}.log", "wb"),
                                   stderr=subprocess.STDOUT, start_new_session=True)
            for attempt in range(100):
                if app.poll() is not None:
                    raise RuntimeError("Responsive title app exited")
                result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                        env=env, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    window = result.stdout.splitlines()[0]
                    break
                time.sleep(.1)
            else:
                raise RuntimeError("Responsive title did not open")
            time.sleep(.3)
            capture(f"title-{width}x{height}")
            pointer(width // 2, height - 144)
            assert (level_directory / "run.dat").read_bytes() == bytes([57, 3, 0, 0, 0, 0]), "Continue did not start the highest unlocked level with fresh stats"
            key("space", "q")
            capture(f"continue-title-{width}x{height}")
            pointer(width // 2, height - 70)
            assert (level_directory / "run.dat").read_bytes() == bytes([0, 3, 0, 0, 0, 0]), "Play did not start from level one"
            assert (level_directory / "unlocked.dat").read_bytes() == bytes([57]), "Play erased unlocked progress"
            key("space", "q")
            key("l")  # Choose level.
            capture(f"levels-{width}x{height}")
            # Future Pinewood cards show only a lock and cannot start.
            pointer(width - 36, 96)
            columns = 2 if width - 24 < 560 else 3 if width - 24 < 900 else 4
            card_width = (width - 40 - (columns - 1) * 12) / columns
            card_height = (card_width - 16) * (4 / 3 if height > width else .75) + 44
            pointer(round(12 + card_width / 2), round(132 + card_height / 2))
            assert (level_directory / "run.dat").read_bytes()[0] == 0, "a locked level started"
            capture(f"levels-locked-{width}x{height}")
            pointer(36, 96)  # Back to Leafwood.
            # Scrolling moves the grid while keeping chapter controls fixed.
            capture(f"levels-scroll-before-{width}x{height}")
            subprocess.run(["xdotool", "mousemove", "--window", window, "--sync", str(width // 2), str(height - 40),
                            "click", "--repeat", "10", "--delay", "35", "5"], env=env, check=True)
            time.sleep(.2)
            capture(f"levels-scroll-after-{width}x{height}")
            before = numpy.asarray(Image.open(OUT / f"levels-scroll-before-{width}x{height}.png"))
            after = numpy.asarray(Image.open(OUT / f"levels-scroll-after-{width}x{height}.png"))
            assert not numpy.array_equal(before[132:], after[132:]), "level cards did not scroll"
            pointer(36, 96)  # Meadow, resets the scroll position.
            pointer(width - 36, 96)  # Leafwood again.
            pointer(round(12 + card_width / 2), round(132 + card_height / 2))
            assert (level_directory / "run.dat").read_bytes() == bytes([40, 3, 0, 0, 0, 0]), "an unlocked level did not start fresh"
            assert (level_directory / "unlocked.dat").read_bytes() == bytes([57]), "selecting an earlier level reduced progress"
            time.sleep(.15)
            key("space")
            capture(f"play-{width}x{height}")
        print("Private UI local test: Try again, Continue, Play and the scrollable unlocked-level selector worked in portrait and landscape.")

        # Real held pointer input: turns must take effect before mouseup,
        # including subsequent corners during that very same contact.
        for width, height in ((640, 480), (320, 568)):
            stop(app)
            log = OUT / f"steering-{width}x{height}.log"
            env.update(WURM_PROBE_WIDTH=str(width), WURM_PROBE_HEIGHT=str(height),
                       WURM_PROBE_SCENE="1", WURM_PROBE_STEERING="1", WURM_PROBE_MODE="1")
            app = subprocess.Popen([str(ROOT / "build/Apfelwurm-modal-test")], cwd=ROOT, env=env,
                                   stdout=open(log, "wb"), stderr=subprocess.STDOUT, start_new_session=True)
            for attempt in range(100):
                if app.poll() is not None:
                    raise RuntimeError(log.read_text()[-1000:])
                result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                        env=env, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    window = result.stdout.splitlines()[0]
                    break
                time.sleep(.05)
            else:
                raise RuntimeError("No owned steering probe")
            time.sleep(.15)
            x, y = width // 2, height // 2
            subprocess.run(["xdotool", "mousemove", "--window", window, "--sync", str(x), str(y),
                            "mousedown", "1"], env=env, check=True)
            time.sleep(.08)
            try:
                for direction, dx, dy in ((2, 14, 0), (3, 14, 14), (0, 0, 14)):
                    subprocess.run(["xdotool", "mousemove", "--window", window, "--sync",
                                    str(x + dx), str(y + dy)], env=env, check=True)
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline:
                        if f"steering={direction} touch=1" in log.read_text():
                            break
                        time.sleep(.02)
                    else:
                        raise AssertionError("Held-contact turn missing: " + log.read_text())
                capture(f"held-steering-{width}x{height}")
            finally:
                subprocess.run(["xdotool", "mouseup", "1"], env=env, check=True)
        env.pop("WURM_PROBE_STEERING", None)
        print("Private UI local test: right, down and left turns took effect before release in both orientations.")

        # The saved pad choice drives the same actual pointer path. Sliding
        # between arms must steer while one contact remains held.
        (level_directory / "controls.dat").write_bytes(bytes([1]))
        for width, height in ((640, 480), (320, 568)):
            stop(app)
            log = OUT / f"pad-{width}x{height}.log"
            env.update(WURM_PROBE_WIDTH=str(width), WURM_PROBE_HEIGHT=str(height),
                       WURM_PROBE_SCENE="1", WURM_PROBE_STEERING="1", WURM_PROBE_MODE="1")
            app = subprocess.Popen([str(ROOT / "build/Apfelwurm-modal-test")], cwd=ROOT, env=env,
                                   stdout=open(log, "wb"), stderr=subprocess.STDOUT, start_new_session=True)
            for attempt in range(100):
                if app.poll() is not None:
                    raise RuntimeError(log.read_text()[-1000:])
                result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                        env=env, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    window = result.stdout.splitlines()[0]
                    break
                time.sleep(.05)
            else:
                raise RuntimeError("No owned direction-pad probe")
            time.sleep(.15)
            short = min(width, height - (104 if width < 520 else 72))
            margin = min(32, max(24, short * .06))
            side = min(216, max(168, short * .44))
            left, top = margin, height - side - margin
            try:
                for direction, x, y in ((2, left + side * .84, top + side * .5),
                                        (3, left + side * .5, top + side * .84),
                                        (0, left + side * .16, top + side * .5)):
                    subprocess.run(["xdotool", "mousemove", "--window", window, "--sync", str(round(x)), str(round(y)),
                                    *(["mousedown", "1"] if direction == 2 else [])], env=env, check=True)
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline:
                        if f"steering={direction} touch=1" in log.read_text():
                            break
                        time.sleep(.02)
                    else:
                        raise AssertionError("Held direction-pad turn missing: " + log.read_text())
                capture(f"direction-pad-{width}x{height}")
            finally:
                subprocess.run(["xdotool", "mouseup", "1"], env=env, check=True)
        (level_directory / "controls.dat").write_bytes(bytes([0]))
        env.pop("WURM_PROBE_STEERING", None)
        print("Private UI local test: saved direction-pad choice and held arm changes steer in both orientations.")

        # A playtest uses the selected editor layout even in a window of
        # the other shape; the two choices are not a viewport-dependent turn.
        for width,height,layout,columns,rows in ((320,568,0,40,30),(640,480,1,30,40)):
            stop(app)
            log=OUT/f"layout-{layout}-{width}x{height}.log"
            env.update(WURM_PROBE_WIDTH=str(width),WURM_PROBE_HEIGHT=str(height),WURM_PROBE_LEVEL="1",
                       WURM_PROBE_SCENE="0",WURM_PROBE_EDITOR_LAYOUT=str(layout),WURM_PROBE_MODE="1")
            app=subprocess.Popen([str(ROOT/"build/Apfelwurm-modal-test")],cwd=ROOT,env=env,
                                 stdout=open(log,"wb"),stderr=subprocess.STDOUT,start_new_session=True)
            for attempt in range(100):
                if app.poll() is not None:raise RuntimeError(log.read_text()[-1000:])
                result=subprocess.run(["xdotool","search","--onlyvisible","--pid",str(app.pid)],env=env,capture_output=True,text=True)
                if result.returncode==0 and result.stdout.strip():
                    window=result.stdout.splitlines()[0];break
                time.sleep(.05)
            else:raise RuntimeError("No owned orientation playtest")
            time.sleep(.2)
            assert f"board={columns}x{rows}" in log.read_text(), log.read_text()
            capture(f"editor-playtest-{columns}x{rows}")
        env.pop("WURM_PROBE_EDITOR_LAYOUT",None)
        print("Private UI local test: independent portrait edits survive mode switches; both playtest layouts ignore window shape.")

        # Turning a running game selects its other board and preserves the
        # paused state, lives and score. Only this owned Xvfb window is resized.
        stop(app)
        log=OUT/"rotate-active.log"
        env.update(WURM_PROBE_WIDTH="640",WURM_PROBE_HEIGHT="480",WURM_PROBE_LEVEL="1",
                   WURM_PROBE_SCENE="0",WURM_PROBE_MODE="2")
        app=subprocess.Popen([str(ROOT/"build/Apfelwurm-modal-test")],cwd=ROOT,env=env,
                             stdout=open(log,"wb"),stderr=subprocess.STDOUT,start_new_session=True)
        for attempt in range(100):
            if app.poll() is not None:raise RuntimeError(log.read_text()[-1000:])
            result=subprocess.run(["xdotool","search","--onlyvisible","--pid",str(app.pid)],env=env,capture_output=True,text=True)
            if result.returncode==0 and result.stdout.strip():
                window=result.stdout.splitlines()[0];break
            time.sleep(.05)
        else:raise RuntimeError("No owned rotation probe")
        time.sleep(.15)
        for width,height,columns,rows in ((320,568,30,40),(640,480,40,30)):
            subprocess.run(["xdotool","windowsize",window,str(width),str(height)],env=env,check=True)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                if f"board={columns}x{rows} lives=3 score=1234 mode=2" in log.read_text():break
                time.sleep(.05)
            else:raise AssertionError("Rotation lost board orientation or run state: "+log.read_text())
            capture(f"rotate-level-2-{columns}x{rows}")
        print("Private UI local test: rotating level 2 loads the other layout, preserving pause, lives and score.")

        # Render an actual board from every landscape, without a modal.
        for chapter, level in (("meadow", 0), ("leafwood", 40), ("pinewood", 80), ("lake", 120), ("mountains", 160)):
            stop(app)
            log = OUT / (chapter + ".log")
            env.update(WURM_PROBE_WIDTH="640", WURM_PROBE_HEIGHT="480", WURM_PROBE_SCENE="7",
                       WURM_PROBE_MODE="1", WURM_PROBE_LEVEL=str(level))
            app = subprocess.Popen([str(ROOT / "build/Apfelwurm-modal-test")], cwd=ROOT, env=env,
                                   stdout=open(log, "wb"), stderr=subprocess.STDOUT, start_new_session=True)
            for attempt in range(100):
                if app.poll() is not None:
                    raise RuntimeError(log.read_text()[-1000:])
                result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                        env=env, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    window = result.stdout.splitlines()[0]
                    break
                time.sleep(.05)
            else:
                raise RuntimeError("No owned landscape probe")
            time.sleep(.2)
            capture("landscape-" + chapter)
        env["WURM_PROBE_LEVEL"] = "0"

        # Show the full, bent worm and both gates without a modal obscuring
        # them. These scenes use only the separate test host and no clock.
        for width, height in ((960, 600), (320, 568)):
            for scene, label in ((1, "entrance"), (2, "exit"), (3, "zero-lives"),
                                 (4, "entering"), (5, "leaving"), (6, "downward"), (7, "walls"), (8, "forest-walls")):
                stop(app)
                name = f"gameplay-{width}x{height}-{label}"
                log = OUT / (name + ".log")
                env.update(WURM_PROBE_WIDTH=str(width), WURM_PROBE_HEIGHT=str(height),
                           WURM_PROBE_SCENE=str(scene), WURM_PROBE_MODE="1",
                           WURM_PROBE_LEVEL="40" if scene == 8 else "0")
                app = subprocess.Popen([str(ROOT / "build/Apfelwurm-modal-test")], cwd=ROOT, env=env,
                                       stdout=open(log, "wb"), stderr=subprocess.STDOUT, start_new_session=True)
                for attempt in range(100):
                    if app.poll() is not None:
                        raise RuntimeError(f"{name} exited: {log.read_text()[-1000:]}")
                    result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                            env=env, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        window = result.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                else:
                    raise RuntimeError("No owned gameplay probe window")
                time.sleep(.3)
                capture(name)
                if scene == 3:
                    assert "mode=3 lives=0" in log.read_text(), "game over did not stop at zero lives"
                    continue
                picture = numpy.asarray(Image.open(OUT / (name + ".png")).convert("RGB"), dtype=int)
                columns, rows = (30, 40) if height > width else (40, 30)
                bar = 104 if width < 520 else 72
                scale = min(width / (columns * 16), (height - bar) / (rows * 16))
                left = (width - columns * 16 * scale) / 2
                top = bar + (height - bar - rows * 16 * scale) / 2

                def patch(x0, y0, x1, y1):
                    return picture[max(0, round(y0)):min(height, round(y1)),
                                   max(0, round(x0)):min(width, round(x1))]

                def orange(pixels):
                    return ((pixels[:, :, 0] > 90) & (pixels[:, :, 1] > 35) &
                            (pixels[:, :, 2] < 140) & (pixels[:, :, 0] > pixels[:, :, 1] * 1.15))

                row = 0 if scene in (2, 5) else rows - 1
                for column in (columns // 2 - 1, columns // 2 + 1):
                    stone = patch(left + (column * 16 + 2) * scale, top + (row * 16 + 2) * scale,
                                  left + (column * 16 + 14) * scale, top + (row * 16 + 14) * scale)
                    neutral = stone.max(axis=2) - stone.min(axis=2) < 55
                    assert neutral.mean() > .25, name + " is missing a stone gate post"
                head_x = columns // 2 * 16 + 8
                head_y = rows // 2 * 16 + 8
                if scene == 1:
                    chip_x = 12 if width < 520 else 334
                    chip_y = 60 if width < 520 else 16
                    hearts = patch(chip_x, chip_y, chip_x + (width - 40) / 3 if width < 520 else chip_x + 108, chip_y + 34)
                    red = (hearts[:, :, 0] > 180) & (hearts[:, :, 0] > hearts[:, :, 1] * 1.5)
                    occupied = red.any(axis=0)
                    groups = int(occupied[0]) + int((occupied[1:] & ~occupied[:-1]).sum())
                    assert groups == 3, name + " must show three separate life hearts"
                if scene in (1, 2):
                    ribbon = orange(patch(left + (head_x - 140) * scale, top + head_y * scale - 2,
                                          left + (head_x - 32) * scale, top + head_y * scale + 3))
                    assert ribbon.any(axis=0).mean() > .9, name + " has large gaps between body segments"
                    face = orange(patch(left + (head_x - 10) * scale, top + (head_y - 13) * scale,
                                        left + (head_x + 10) * scale, top + (head_y + 13) * scale)).any(axis=1)
                    body = orange(patch(left + (head_x - 61) * scale, top + (head_y - 13) * scale,
                                        left + (head_x - 59) * scale, top + (head_y + 13) * scale)).any(axis=1)
                    face_rows, body_rows = numpy.flatnonzero(face), numpy.flatnonzero(body)
                    assert len(body_rows) > 3 and len(face_rows) > 3, "worm artwork missing"
                    assert face_rows[-1] - face_rows[0] >= body_rows[-1] - body_rows[0], "head is smaller than the body"
                elif scene == 6:
                    head = patch(left + (head_x - 12) * scale, top + (head_y - 12) * scale,
                                 left + (head_x + 12) * scale, top + (head_y + 12) * scale)
                    blue = (head[:, :, 2] > head[:, :, 0] * 1.1) & (head[:, :, 2] > head[:, :, 1] * 1.05)
                    assert blue.any(), name + " has no visible directional eyes"
                elif scene in (7, 8):
                    wall = patch(left + 6 * 16 * scale, top + (6 * 16 + 3) * scale,
                                 left + (columns - 7) * 16 * scale, top + (8 * 16 - 3) * scale)
                    if scene == 7:
                        assert (wall[:, :, 0] < 130).mean() > .9, name + " has gaps in the joined hedge"
                    else:
                        assert wall[:, :, 1].mean() < 125, name + " has missing forest canopy"
                else:
                    opening = patch(left + columns // 2 * 16 * scale, top + row * 16 * scale,
                                    left + (columns // 2 + 1) * 16 * scale, top + (row + 1) * 16 * scale)
                    assert orange(opening).sum() > 2, name + " hides the head while it passes through the gate"
        print("Private UI local test: stone gates, long spaced body, directional head and zero-life game over passed in landscape and portrait.")
    finally:
        os.close(read_fd)
        stop(app)
        stop(server)


if __name__ == "__main__":
    main()
