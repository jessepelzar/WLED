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
