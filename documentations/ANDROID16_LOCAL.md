# Local Android 16 image

Build from the repository root in PowerShell with Docker Desktop running Linux containers:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
docker build -f docker/base/Dockerfile --build-arg DOCKER_ANDROID_VERSION=local-16 -t budtmo/docker-android:base_local-16 .
# Continue only if the base build succeeds.
docker build -f docker/emulator/Dockerfile --build-arg DOCKER_ANDROID_VERSION=local-16 --build-arg EMULATOR_ANDROID_VERSION=16.0 --build-arg EMULATOR_API_LEVEL=36 -t docker-android-local:16.0 .
```

The emulator Dockerfile installs the repository CLI and its logging configuration directly; it does not need the private `extension.sh` secret. SDK downloads require accepting Google's Android SDK licenses, as in the existing Dockerfile.

Enable KVM on this Windows/WSL2 host if `/dev/kvm` is absent, then start the emulator:

```powershell
wsl -d docker-desktop -- modprobe kvm_intel
docker compose -f docker-compose.android16.yml up -d
```

Open <http://127.0.0.1:6080>. Only the local computer can access the published port. Analytics is disabled; Appium and MCP are not started. Android user data persists in the `android16-data` Compose volume. On the current host, Docker's disk is already under `H:\Docker\DockerDesktopWSL`; image layers, cache and the volume use that disk, not the C: drive. Other hosts must check Docker's disk location separately.

Verify startup (boot completion takes time):

```powershell
docker exec android16-local adb -s emulator-5554 shell getprop ro.build.version.release
docker exec android16-local adb -s emulator-5554 shell getprop ro.build.version.sdk
docker exec android16-local adb -s emulator-5554 shell getprop sys.boot_completed
docker exec android16-local cat /home/androidusr/device_status
```

Expected: `16`, `36`, `1`, `READY`. Inspect startup failures with `docker logs android16-local` and `docker exec android16-local tail -n 80 /home/androidusr/logs/device.stdout.log`.

Stop with `docker compose -f docker-compose.android16.yml stop`; start again with `up -d`. Do not use `down -v` unless deliberately deleting Android data. KVM module availability must be checked again after Docker/WSL restarts. API mapping alone is not a compatibility guarantee; actual boot and UI evidence is recorded in `work/android16-progress.md`.

The full-home volume also contains a copy of the app scripts. After rebuilding an image, replacing the container alone does not refresh those volume files. Preserve the volume and back up its data before deliberately migrating or refreshing app files; do not delete it to apply an image update.

## Verified setup and failure notes (2026-11-11)

On Docker Desktop Linux/WSL2 with usable KVM, the local image built successfully (~10.7 GiB). The installed CLI import gate passed; all 26 CLI unit tests passed inside Linux. First boot and a subsequent Compose stop/start both reported Android `16`, SDK `36`, boot completed `1` and device status `READY`. The noVNC page returned HTTP 200, its WebSocket returned the VNC `RFB 003.008` banner, and an ADB screenshot showed a rendered Android UI.

Two source fixes are essential when reproducing this build:

- Installing the original Python package produced `ModuleNotFoundError: app`: the console entry point used `app:cli`, but `py_modules` named other modules. Package `app.py` and `logger/logging.conf`, and retain the Dockerfile's `docker-android --help` build gate. A copied source tree alone does not verify the installed package.
- KVM setup previously deleted the first `/etc/passwd` row after changing device ownership. Preserve user accounts; only change KVM ownership. The regression test rejects that extra command, and the real container stop/start check confirms `root` remains available.

The initial full-suite attempt on Windows hit three symlink privilege errors; the Linux run passed without changing those tests. Startup also emitted PulseAudio and modem IPv6 warnings. They did not prevent boot, GUI rendering or noVNC; audio and modem functionality were not verified. No APK/application compatibility or browser mouse/keyboard E2E test was performed.
