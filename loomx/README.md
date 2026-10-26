# Loomx WLED fork

This repository keeps Loomx firmware changes on the `loomx` branch while
tracking official, stable WLED releases from `wled/WLED`.

## Where Loomx changes belong

- Put replacement web UI files in `loomx/ui/`, using the same relative paths as
  `wled00/data/`. For example, `loomx/ui/index.htm` replaces
  `wled00/data/index.htm` only while building.
- Put other Loomx-only tooling and documentation under `loomx/` when possible.
- Avoid editing `wled00/data/` directly. Keeping the UI as an overlay prevents
  an upstream WLED merge from overwriting it.
- Firmware changes that cannot be isolated under `loomx/` can still be committed
  normally. Git will preserve them during upstream merges unless WLED changes
  the same lines.

The empty `loomx/ui/` directory is intentional. Copy only the WLED UI files you
want to replace. Files not present in the overlay continue to come from the
current WLED release.

## Build the Loomx UI

Install WLED's dependencies once:

```sh
npm ci
```

Then build the normal WLED UI with the Loomx overlay applied in a temporary
directory:

```sh
node loomx/tools/build-ui.mjs
```

This writes WLED's generated `wled00/html_*.h` and `wled00/js_*.h` files without
modifying the tracked source files in `wled00/data/`.

Run the normal validation afterward:

```sh
npm test
pio run -e esp32dev
```

## Loomx firmware versions

The user-facing firmware version lives in `loomx/VERSION` and uses semantic
versioning, such as `1.0.0`. PlatformIO embeds that value in `/json/info`, while
the Supabase publisher writes the same value to each controller manifest and
release record.

`Build and Upload WLED.command` increments the patch number at the start of
every build run, then embeds and publishes that same new version for both VX4
and VX8. A failed build does not reuse its number on the next run.

Every PlatformIO build also verifies that the selected version is embedded in
both controller binaries and writes clearly named local artifacts:

```text
build_output/release/Loomx_WLED_<version>_VX4.bin
build_output/release/Loomx_WLED_<version>_VX8.bin
```

## Stable WLED updates

`.github/workflows/loomx-upstream-sync.yml` checks every day for the newest
stable WLED tag (release candidates and beta tags are excluded). When a newer
release is available, it:

1. merges the official tag into `loomx`;
2. builds the overlaid UI and runs the Node tests;
3. pushes the merge only if validation succeeds.

Run the same merge locally with:

```sh
loomx/tools/sync-upstream.sh
```

The UI overlay is stored separately, so a WLED update cannot replace it. No Git
workflow can guarantee that a fully redesigned UI remains compatible with every
future WLED API change. If a real code conflict or validation failure occurs,
automation leaves `loomx` unchanged and opens a GitHub issue for review instead
of discarding Loomx work or shipping an unvalidated update.

## Remotes and branches

- `origin`: `jessepelzar/WLED`, the writable fork
- `upstream`: `wled/WLED`, the official source
- `loomx`: stable WLED plus Loomx changes; this is the fork's default branch
- `main`: untouched upstream development history

## Output brightness and locks

Open an output on Home (or its Brightness button under Outputs) to set 0–100%.
The controller stores the rounded 0–255 value: 0% = 0, 50% = 128, 100% = 255.
Unlocked output levels scale with master brightness. Locking captures the current
effective level, so subsequent master changes, including zero, leave it unchanged.
Explicit power-off still switches all outputs off. Levels and locks survive reboot.

Changing a locked level or changing a lock requires the hardware/settings PIN,
entered afresh in the brightness dialog. Home also offers **Lock all brightnesses**.
The live-data screen exposes the same controls without overriding the incoming stream.

Configuration stores `bri` and `briLock` on each `hw.led.ins` entry. Brightness-only
updates use `hw.led.outputBri`, an array of `{id, bri?, lock?}` objects, so they do not
rebuild LED buses. A lock-only update captures the current level; an explicit `bri`
sets the new level. Configuration writes require the configured PIN in the request.
`/json/state` reports `outputBri` entries and the actual `masterBri` (including zero).

## Wi-Fi setup and names

Fresh setup and a factory-reset reboot use `Loomx` for the AP SSID and device
name. Existing saved custom names still load from configuration; VX4/VX8 remain
product identifiers rather than default device names. On the first boot of this
firmware, known saved factory names (`WLED`, `Dig-Octa-32-8L`, `VX4`, `VX8`,
`Loomx Node`, and AP names `WLED-AP`, `Loomx-AP`, `Loomx Node`) migrate to
`Loomx`. Configuration records `id.loomxNames` so subsequent explicit name edits
are preserved, including edits back to an old factory name. No reset is needed.

The Wi-Fi dialog and overlaid Wi-Fi settings page start a scan with
`GET /json/net?scan=1` and poll with `scan=0`. The response retains `networks`
and adds `scan`: `running`, `complete`, or `error`. Empty completed scans are
valid. Repeated UI requests share the in-progress scan, and reconnect handling
waits until the results are collected. An abandoned browser releases that
protection after 15 seconds; the radio's scan timeout still reports a real error.

Regression coverage lives in `tools/wifi-test.js`, including the actual firmware
scan serializer compiled against the bundled ArduinoJson header with a fake
radio. Run `node --test tools/wifi-test.js` or the full `npm test` suite.

Hardware acceptance checks after flashing:

- Start with erased configuration, then repeat after a factory reset: confirm the
  AP SSID and `/json/info` device name are both exactly `Loomx`.
- Save distinct custom AP/device names and reboot or update firmware: confirm
  both names persist. A complete factory reset erases those saved settings.
- From AP setup, press Connect to Wi-Fi once: loading must continue until the
  network list or an error appears. Repeat while scanning and after completion.
- Select a secured network, enter its password, and join; also try an open
  network. Confirm the selected SSID and assigned IP in the UI and after reboot.
- Try unreachable/incorrect credentials and confirm fallback AP access; verify
  scans while disconnected, connected, and with multiple saved profiles.

## OTA update authorization

Installing a release and opening local firmware upload show an Update code
card. Enter the controller's four-digit Settings PIN. Incorrect
codes and retry cooldowns appear in the card and can be retried. Cancelling
keeps installation stopped. The code is not saved to browser storage.

The UI validates the code with `POST /loomx/security/unlock` and revalidates it
just before uploading, after download and checksum verification. This endpoint
authorizes the existing Settings PIN session without modifying configuration
and retains the firmware's PIN retry cooldown. The separate OTA passphrase
lock has been removed from the firmware and both settings screens. Legacy
`ota.lock`, `ota.lock-wifi`, `ota.pwd` and `ota.psk` fields are ignored and are
no longer saved. Update controls are directly available regardless of previous
browser enable/disable preferences. Regression tests are in
`tools/ota-code-test.js`.

## LED count indicator

Changing an output's pixel count lights its complete configured run in dim
white for two seconds, then fades it to black over one second. Further count
changes restart the indicator. Shrinking or deleting an output sends black
through the old driver before releasing it, so removed pixels do not stay lit.
Zero-count digital outputs retain their pin, type, brightness and other settings
as disabled outputs; increasing from zero starts the same preview.

The firmware owns the timer and renders directly on the physical output, so the
indicator finishes after leaving the page and covers pixels omitted by segments
or LED maps. It temporarily shows at master brightness zero, retains configured
current limiting, and leaves saved brightness, locks, colors and stream settings
unchanged. After the fade, the underlying lighting or live stream resumes.
Booting with an unchanged count does not trigger a preview.

`tools/led-count-preview-test.js` compiles the actual preview timer, resize logic,
bus configuration and digital pixel writer with a simulated LED driver. After
flashing, check increasing and decreasing counts, rapid changes, zero and back,
reversed/RGBW outputs, and two outputs with different counts. Confirm the exact
lit length and fade on hardware, also with master brightness zero and live data.
