#!/usr/bin/env python3
"""Render the recovered MIDI offline, without connecting to an audio device.

Uses FluidSynth's sample-clock file renderer, documented at
https://www.fluidsynth.org/api/FileRenderer.html . The MIDI events are exact;
the General MIDI soundfont supplies instruments in place of the old OS synth.
"""
import argparse
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import subprocess
import time

os.environ["OMP_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[1]


def render(midi, soundfont, target):
    lib = C.CDLL(ctypes.util.find_library("fluidsynth"))

    def api(name, result, *arguments):
        fn = getattr(lib, name)
        fn.restype = result
        fn.argtypes = list(arguments)
        return fn

    pointer, integer, text = C.c_void_p, C.c_int, C.c_char_p
    settings_new = api("new_fluid_settings", pointer)
    setstr = api("fluid_settings_setstr", integer, pointer, text, text)
    setint = api("fluid_settings_setint", integer, pointer, text, integer)
    setnum = api("fluid_settings_setnum", integer, pointer, text, C.c_double)
    synth_new = api("new_fluid_synth", pointer, pointer)
    font_load = api("fluid_synth_sfload", integer, pointer, text, integer)
    player_new = api("new_fluid_player", pointer, pointer)
    player_add = api("fluid_player_add", integer, pointer, text)
    player_play = api("fluid_player_play", integer, pointer)
    player_status = api("fluid_player_get_status", integer, pointer)
    renderer_new = api("new_fluid_file_renderer", pointer, pointer)
    renderer_block = api("fluid_file_renderer_process_block", integer, pointer)
    settings = settings_new()
    synth = player = renderer = None
    wave = target.with_suffix(".render.wav")
    try:
        for name, value in ((b"audio.file.name", os.fsencode(wave)), (b"audio.file.type", b"wav"),
                            (b"audio.file.format", b"s16"), (b"player.timing-source", b"sample")):
            if setstr(settings, name, value) < 0:
                raise RuntimeError(f"FluidSynth rejected {name!r}")
        setint(settings, b"synth.cpu-cores", 1)
        setint(settings, b"synth.lock-memory", 0)
        setnum(settings, b"synth.sample-rate", 22050.0)
        setnum(settings, b"synth.gain", 0.5)
        synth = synth_new(settings)
        if not synth or font_load(synth, os.fsencode(soundfont), 1) < 0:
            raise RuntimeError("Could not load the MIDI soundfont")
        player = player_new(synth)
        if not player or player_add(player, os.fsencode(midi)) != 0 or player_play(player) != 0:
            raise RuntimeError("Could not load recovered MIDI")
        renderer = renderer_new(synth)
        if not renderer:
            raise RuntimeError("Could not create offline renderer")
        deadline = time.monotonic() + 45
        while player_status(player) == 1:
            if renderer_block(renderer) != 0:
                raise RuntimeError("Offline MIDI render failed")
            if time.monotonic() > deadline:
                raise RuntimeError("Offline MIDI render exceeded its time budget")
    finally:
        if player:
            api("fluid_player_stop", integer, pointer)(player)
            api("fluid_player_join", integer, pointer)(player)
        if renderer:
            api("delete_fluid_file_renderer", None, pointer)(renderer)
        if player:
            api("delete_fluid_player", None, pointer)(player)
        if synth:
            api("delete_fluid_synth", None, pointer)(synth)
        api("delete_fluid_settings", None, pointer)(settings)
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(wave),
                    "-ac", "1", "-ar", "22050", "-f", "s16le", str(target)], check=True, timeout=20)
    wave.unlink()
    print(f"Rendered {midi.name}: {target.stat().st_size // 44100} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soundfont", type=Path, default=Path("/usr/share/sounds/sf2/TimGM6mb.sf2"))
    args = parser.parse_args()
    for track in range(1, 4):
        base = ROOT / f"assets/original/wurm{track}"
        render(base.with_suffix(".mid"), args.soundfont, base.with_suffix(".pcm"))
