"""Exercise Wurm's existing scaffold command and inspect a fixture APK.

Run under build-queue. This builds no game library, sends no notification and
never installs or executes the fixture APK.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"
RECEIVER = "org.kryonlabs.notifications.NotificationReceiver"
PERMISSIONS = {"android.permission.POST_NOTIFICATIONS", "android.permission.RECEIVE_BOOT_COMPLETED"}
ACTIONS = {"android.intent.action.BOOT_COMPLETED", "android.intent.action.TIME_SET",
           "android.intent.action.TIMEZONE_CHANGED", "android.intent.action.MY_PACKAGE_REPLACED"}


def run(*args):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def verify_apk(apk, tools):
    manifest = run(tools / "aapt", "dump", "xmltree", apk, "AndroidManifest.xml")
    assert all(name in manifest for name in PERMISSIONS | ACTIONS | {RECEIVER})
    output = ROOT / "work/android-notification-apk-test"
    output.mkdir(parents=True, exist_ok=True)
    symbols = {"JNI_OnLoad", "Java_org_kryonlabs_notifications_NotificationReceiver_receive",
               "Java_org_kryonlabs_notifications_NotificationReceiver_requestPermission"}
    with zipfile.ZipFile(apk) as archive:
        dex = [name for name in archive.namelist() if name.endswith(".dex")]
        assert any(b"Lorg/kryonlabs/notifications/NotificationReceiver;" in archive.read(name) for name in dex)
        for abi in ("arm64-v8a", "armeabi-v7a"):
            library = output / (abi + ".so")
            library.write_bytes(archive.read("lib/" + abi + "/libmain.so"))
            exported = run("readelf", "--dyn-syms", "--wide", library)
            rows = [line.split() for line in exported.splitlines()]
            names = {row[7] for row in rows if len(row) >= 8 and row[3] == "FUNC"
                     and row[4] in {"GLOBAL", "WEAK"} and row[5] == "DEFAULT" and row[6] != "UND"}
            assert symbols <= names, (str(apk), abi, "missing exported receiver JNI", sorted(symbols - names))
    print(str(apk) + ": reminder manifest, receiver DEX and both ARM receiver JNI exports passed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kryon", type=Path)
    parser.add_argument("--apk", action="append", type=Path, default=[])
    args = parser.parse_args()
    sdk = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
               or Path.home() / "Android/Sdk")
    tools = sdk / "build-tools/36.0.0"
    android_jar = sdk / "platforms/android-36/android.jar"
    assert android_jar.is_file() and (tools / "aapt2").is_file(), "Android SDK 36 required"
    if args.apk:
        for apk in args.apk:
            verify_apk(apk, tools)
        return
    if args.kryon is None:
        parser.error("give --kryon for the scaffold fixture or --apk for a built universal APK")
    kryon = args.kryon.resolve()
    fixture = ROOT / "build/android-notification-packaging-test"
    if fixture.exists():
        shutil.rmtree(fixture)
    fixture.mkdir(parents=True)
    scaffold = [sys.executable, kryon / "scripts/android_scaffold.py", "--root", fixture,
                "--name", "Apfelwurm", "--package", "xyz.waozi.wurm", "--activity", "MainActivity",
                "--kryon", kryon]
    run(*scaffold)
    main_dir = fixture / "droid/app/src/main"
    manifest = main_dir / "AndroidManifest.xml"
    # The actual Wurm build keeps its old manifest between scaffold calls.
    original = ROOT / "droid/app/src/main/AndroidManifest.xml"
    tree = ET.parse(original if original.exists() else manifest)
    root = tree.getroot()
    for permission in list(root.findall("uses-permission")):
        if permission.get(ANDROID + "name") in PERMISSIONS:
            root.remove(permission)
    app = root.find("application")
    assert app is not None
    for receiver in list(app.findall("receiver")):
        if receiver.get(ANDROID + "name") == RECEIVER:
            app.remove(receiver)
    app.set(ANDROID + "allowBackup", "false")
    ET.SubElement(app, "activity", {ANDROID + "name": ".KeepRoute", ANDROID + "exported": "false"})
    ET.SubElement(root, "uses-permission", {ANDROID + "name": "android.permission.ACCESS_NETWORK_STATE"})
    ET.register_namespace("android", ANDROID[1:-1])
    tree.write(manifest, encoding="utf-8", xml_declaration=True)
    receiver_path = main_dir / "java/org/kryonlabs/notifications/NotificationReceiver.java"
    receiver_path.write_text("// stale scaffold receiver\n")
    run(*scaffold)
    repaired = ET.parse(manifest).getroot()
    repaired_app = repaired.find("application")
    assert repaired_app is not None and repaired_app.get(ANDROID + "allowBackup") == "false"
    assert any(x.get(ANDROID + "name") == ".KeepRoute" for x in repaired_app.findall("activity"))
    permissions = [x.get(ANDROID + "name") for x in repaired.findall("uses-permission")]
    assert "android.permission.ACCESS_NETWORK_STATE" in permissions
    assert all(permissions.count(name) == 1 for name in PERMISSIONS)
    receivers = [x for x in repaired_app.findall("receiver") if x.get(ANDROID + "name") == RECEIVER]
    assert len(receivers) == 1 and receivers[0].get(ANDROID + "exported") == "false"
    assert {x.get(ANDROID + "name") for x in receivers[0].findall("intent-filter/action")} == ACTIONS
    canonical = kryon / "templates/droid/droid/app/src/main/java/org/kryonlabs/notifications/NotificationReceiver.java"
    assert receiver_path.read_bytes() == canonical.read_bytes()
    once = manifest.read_bytes()
    run(*scaffold)
    assert manifest.read_bytes() == once, "repeat scaffolding must be idempotent"

    # Build only resources and the canonical receiver, then inspect their APK
    # representation. The real game/native APK still needs its release build.
    resources = main_dir / "res"
    live_resources = ROOT / "droid/app/src/main/res"
    if live_resources.exists():
        shutil.copytree(live_resources, resources, dirs_exist_ok=True)
    icon = resources / "mipmap/ic_launcher.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "assets/app/icon.png", icon)
    repaired.set("package", "xyz.waozi.wurm")
    xml = ET.tostring(repaired, encoding="unicode").replace("${zxPlayer}", "false").replace("${nativeLaunchMode}", "standard")
    manifest.write_text(xml)
    compiled = fixture / "resources.zip"
    run(tools / "aapt2", "compile", "--dir", resources, "-o", compiled)
    apk = fixture / "notifications.apk"
    run(tools / "aapt2", "link", "-I", android_jar, "--manifest", manifest,
        "--min-sdk-version", "21", "--target-sdk-version", "36", "-R", compiled, "-o", apk)
    classes = fixture / "classes"
    classes.mkdir()
    run("javac", "-source", "8", "-target", "8", "-bootclasspath", android_jar, "-d", classes, receiver_path)
    dex = fixture / "dex"
    dex.mkdir()
    run(tools / "d8", "--lib", android_jar, "--min-api", "21", "--output", dex, *classes.rglob("*.class"))
    with zipfile.ZipFile(apk, "a") as archive:
        archive.write(dex / "classes.dex", "classes.dex")
    packaged = run(tools / "aapt", "dump", "xmltree", apk, "AndroidManifest.xml")
    assert all(name in packaged for name in PERMISSIONS | ACTIONS | {RECEIVER})
    with zipfile.ZipFile(apk) as archive:
        assert b"Lorg/kryonlabs/notifications/NotificationReceiver;" in archive.read("classes.dex")
    print("Android reminder packaging local test: preserved manifest routes/preferences, repaired permissions and receiver, repeat idempotence, fixture APK manifest and receiver DEX all passed.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stdout or str(error), file=sys.stderr)
        raise SystemExit(error.returncode)
