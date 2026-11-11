"""One-shot offline metadata repair. Dry-run unless --apply is supplied."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
home = Path("/home/androidusr")
ini = home / ".android/avd/samsung_galaxy_s10_17.0.ini"
config = home / "emulator/config.ini"
text = ini.read_text()
lines = text.splitlines(keepends=True)
wrong_target = "target=android-0\n"
correct_target = "target=android-37.0\n"
if lines.count(wrong_target) + lines.count(correct_target) != 1:
    raise RuntimeError("Unexpected AVD target; refusing repair.")
if "system-images/android-37.0/google_apis/x86_64/" not in config.read_text():
    raise RuntimeError("AVD image is not Android17; refusing repair.")
locks = [home / "emulator" / name for name in ("hardware-qemu.ini.lock", "multiinstance.lock")]
locks = [path for path in locks if path.exists()]
if wrong_target not in lines and not locks:
    print("Target correct, no stale locks; no change.")
    raise SystemExit(0)
print(f"Repair target if needed and remove {len(locks)} offline AVD locks; userdata is not modified.")
if args.apply:
    backup = home / "backup" / datetime.now(timezone.utc).strftime("avd-target-%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(ini, backup / "avd.ini")
    shutil.copy2(config, backup / "config.ini")
    for lock in locks:
        shutil.copy2(lock, backup / lock.name)
        lock.unlink()
    if wrong_target in lines:
        ini.write_text("".join(correct_target if line == wrong_target else line for line in lines))
    print(f"Applied. Metadata backup: {backup}")
else:
    print("Dry-run only. Stop the Android17 container before running --apply.")
