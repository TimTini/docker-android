# Local Android 17 image

This build reuses the CLI/GUI setup described in [Local Android 16](ANDROID16_LOCAL.md). It creates a separate image, Compose project, container and data volume, with noVNC on localhost port 6081. Android 16 remains on port 6080.

On 2026-11-11, `sdkmanager --list --channel=0` reported the stable packages `platforms;android-37.0` (revision 2) and `system-images;android-37.0;google_apis;x86_64` (revision 8). The SDK package suffix is **37.0**; the running Android SDK property is **37**. The runtime map must preserve that package suffix because it is used verbatim by `avdmanager`.

Google's [Android 17 setup](https://developer.android.com/about/versions/17/setup-sdk) identifies API 37. [Emulator release notes](https://developer.android.com/studio/releases/emulator) require at least 4 GiB of phone AVD RAM; this Compose file allocates 4096 MiB and four guest CPU cores. The [API 37 Google-services issue](https://developer.android.com/studio/run/emulator-troubleshooting) requires system-image revision 5 or newer; the selected image is revision 8. Google-account/app functionality still requires its own runtime testing.

From the repository root in PowerShell:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
# Reuse the existing tool base. If absent, build it first:
# docker build -f docker/base/Dockerfile --build-arg DOCKER_ANDROID_VERSION=local-16 -t budtmo/docker-android:base_local-16 .
docker build -f docker/emulator/Dockerfile --build-arg DOCKER_ANDROID_VERSION=local-16 --build-arg EMULATOR_ANDROID_VERSION=17.0 --build-arg EMULATOR_API_LEVEL=37.0 -t docker-android-local:17.0 .
# Continue only after the build succeeds and /dev/kvm is available.
docker compose -f docker-compose.android17.yml up -d
```

The base tag `base_local-16` names the existing SDK/tool base; the emulator build arguments select Android 17. Heavy image, cache and volume data use Docker's current H:-backed disk, as documented for the Android 16 build. No standalone image archive is exported.

Open <http://127.0.0.1:6081/vnc.html?autoconnect=true&resize=scale>. Analytics is disabled; Appium/MCP are not started. The separate Compose project `docker-android17` prevents orphan handling or network changes to the Android 16 project. The full-home volume has the same image-upgrade caveat documented for Android 16.

Verification:

```powershell
docker exec android17-local adb -s emulator-5554 shell getprop ro.build.version.release
docker exec android17-local adb -s emulator-5554 shell getprop ro.build.version.sdk
docker exec android17-local adb -s emulator-5554 shell getprop sys.boot_completed
docker exec android17-local cat /home/androidusr/device_status
# Run tests from the installed package, outside the persistent home/source copy:
docker exec -w /tmp android17-local /opt/docker-android-venv/bin/python -m unittest tests.device.test_emulator tests.device.test_device tests.helper.test_helper
```

Expected: `17`, `37`, `1`, `READY`. Stop with `docker compose -f docker-compose.android17.yml stop`; start again with `up -d`. Do not use `down -v` unless deliberately deleting Android 17 data. Startup logs are available via `docker logs android17-local` and `/home/androidusr/logs/device.stdout.log` inside the container. Current build/runtime evidence is recorded in `work/android17-progress.md`.

## SDK tools and offline recovery

The inherited base has command-line tools 19.0. They created `target=android-0` for the minor API package `android-37.0`; actual boot could complete while ADB screenshots failed with a `hasReadColorBufferDma` assertion. The emulator Dockerfile now installs pinned tools 22.0 first on PATH and validates a newly created AVD's exact target during every build. This fixes the producer; editing an existing AVD alone is not a reproducible build fix.

The initial restart also exposed stale X11 locks under `/tmp` and stale AVD locks in the home volume. Compose uses a volatile `/tmp` and a 30-second stop grace period. The image command uses `exec` so the startup script becomes PID 1 and receives SIGTERM; otherwise the inherited shell wrapper leaves Docker to force-kill it. The CLI shutdown handler requests `adb emu kill` and exits the worker so QEMU can release its AVD locks.

For a volume created by the earlier faulty build, use the one-shot repair below **only while Android 17 is stopped**. It defaults to dry-run, verifies the exact Android 17 target/image, and backs up AVD metadata and the two known lock files under `/home/androidusr/backup/avd-target-<UTC timestamp>` before changing anything. It preserves userdata. The helper cannot detect an emulator in another container; never share this volume with a running emulator.

```powershell
docker compose -f docker-compose.android17.yml stop
if ((docker inspect android17-local --format '{{.State.Running}}').Trim() -ne 'false') { throw 'Android 17 must be stopped' }
$repairScript = (Resolve-Path -LiteralPath '.\scripts\repair-android17-avd.py').Path
# Read-only dry-run:
docker run --rm --user 1300:1301 --mount 'type=volume,source=docker-android17_android17-data,target=/home/androidusr,readonly' --mount "type=bind,source=$repairScript,target=/repair.py,readonly" --entrypoint /opt/docker-android-venv/bin/python docker-android-local:17.0 /repair.py
# Apply only after inspecting the dry-run result:
docker run --rm --user 1300:1301 --mount 'type=volume,source=docker-android17_android17-data,target=/home/androidusr' --mount "type=bind,source=$repairScript,target=/repair.py,readonly" --entrypoint /opt/docker-android-venv/bin/python docker-android-local:17.0 /repair.py --apply
docker compose -f docker-compose.android17.yml up -d
```

Metadata discrepancy: SDK Manager and the installed `package.xml` report system-image revision 8 (`x86_64-37.0_r08.zip`), but its internal `source.properties` reports `Pkg.Revision=7`. Both values were observed; the package metadata requires Emulator 37.2.11 or newer, and this build uses 37.2.13. Do not infer the installed package revision from that properties file alone.

## Verified local result (2026-11-11)

The final local image built successfully (~12.3 GiB). All 28 CLI tests passed against the installed package; testing the source copy in a persistent home volume can otherwise run an older test set. SDK 22.0 generated and validated `target=android-37.0`; the existing AVD metadata was repaired offline with timestamped backups and userdata retained.

First boot and a real stop/start reached release `17`, SDK `37`, boot completed `1` and status `READY`. The script was observed as PID 1. Shutdown logged its SIGTERM handler and `OK: killing emulator`; Docker stopped with exit 143 rather than the earlier forced-kill exit 137. After restart, HTTP returned 200, the noVNC WebSocket returned `RFB 003.008`, and ADB screenshots succeeded with a rendered Android launcher. The earlier screenshot assertion and stale-lock startup failures were not present in the final checks.

Android 16 remained running on port 6080 with its original start time and `READY` state throughout. Android 17 image/cache/volume data use the H:-backed Docker disk. Audio/modem functionality, Google-account sign-in, individual APK compatibility and browser mouse/keyboard E2E were not tested.
