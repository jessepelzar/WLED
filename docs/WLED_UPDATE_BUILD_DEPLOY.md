# WLED update, build, and deployment

`scripts/update-build-deploy-wled.sh` safely updates the custom WLED branch
from the fork and official WLED repository, builds one PlatformIO target,
packages a checksummed firmware release, and optionally publishes it.

The script never stashes or discards work, force-pushes, resolves merge
conflicts, deletes old releases, or stores deployment credentials in Git.

## Detected repository configuration

At the time this workflow was added:

- The custom branch was `loomx`.
- `origin` was the `jessepelzar/WLED` fork.
- `upstream` was the official WLED repository at
  `https://github.com/wled/WLED.git`.
- The upstream default branch was `main`.
- No root `platformio_override.ini` was present.
- `esp32dev` was the appropriate default firmware environment and had already
  built successfully.
- The Loomx UI overlay was built through `loomx/tools/build-ui.mjs`.

The script re-detects branch, remote, upstream default branch, and PlatformIO
environment information on each run. It does not depend solely on this
snapshot.

## macOS prerequisites

Install Git, Python, Node.js, rsync, and ShellCheck with Homebrew:

```bash
brew install git python node rsync shellcheck
```

macOS includes `ssh`, `scp`, and `shasum`. The current WLED package metadata
requires Node.js 20 or newer; the script warns when an older version is found.

Install PlatformIO Core:

```bash
python3 -m pip install --user platformio
```

Alternatively:

```bash
brew install platformio
```

Confirm the tools:

```bash
git --version
python3 --version
node --version
pio --version
ssh -V
```

The script locates PlatformIO as `pio`, `python3 -m platformio`, or the normal
macOS PlatformIO virtual-environment executable at
`~/.platformio/penv/bin/pio`.

## Deployment configuration

Create the ignored local configuration:

```bash
cp .env.wled-deploy.example .env.wled-deploy
${EDITOR:-nano} .env.wled-deploy
```

Use literal `KEY=VALUE` assignments:

```bash
WLED_CUSTOM_BRANCH=loomx
WLED_PIO_ENV=esp32dev
DEPLOY_HOST=firmware.example.com
DEPLOY_USER=deploy
DEPLOY_PATH=/srv/firmware/loomx
DEPLOY_PORT=22
```

The `.env.wled-deploy` parser does not execute the file or expand shell
expressions. Blank lines, comments beginning with `#`, unquoted values, and
values enclosed in matching single or double quotes are supported. Command
substitution and variable interpolation are deliberately not supported.
Process environment variables take precedence over values in the file, and
command-line `--branch` and `--env` values take precedence over both.

These optional variables are also accepted:

```bash
WLED_PROJECT_NAME=loomx-wled
DEPLOY_UPDATE_LATEST=1
DEPLOY_LATEST_NAME=latest.bin
```

`DEPLOY_UPDATE_LATEST=1` is the default. It atomically replaces a symlink named
`latest.bin` only after the versioned binary has uploaded and its remote
SHA-256 digest has been verified. Set it to `0` to leave the stable pointer
unchanged.

The real `.env.wled-deploy` and the generated `releases/` directory are ignored
by Git.

## Double-click build and upload

After `.env.wled-deploy` is configured, open Finder and double-click:

```text
Build and Upload WLED.command
```

The launcher requires no flags. It runs the complete workflow: update from the
fork, merge official WLED, build the configured PlatformIO environment, push
the successful merge, upload the versioned firmware and checksum, validate the
remote checksum, and update `latest.bin`.

The Terminal window remains open after success or failure so the completion
summary or error can be read. The launcher resolves the repository from its own
location, so it works regardless of Finder's starting directory.

## SSH deployment

Use SSH key authentication. For example:

```bash
ssh-keygen -t ed25519 -C "loomx-wled-deploy"
ssh-copy-id -i ~/.ssh/id_ed25519.pub deploy@firmware.example.com
ssh -p 22 deploy@firmware.example.com
```

On macOS, `ssh-copy-id` can be installed with:

```bash
brew install ssh-copy-id
```

The deployment user needs permission to create `DEPLOY_PATH` or write into its
parent directory. The script:

1. uploads the firmware and checksum under temporary names in
   `DEPLOY_PATH`;
2. calculates the firmware SHA-256 digest on the server;
3. compares it with the local digest;
4. renames the temporary files to their final versioned names;
5. updates `latest.bin`, when enabled.

Older releases are never removed.

## Git update behavior

The normal workflow:

1. Requires a completely clean working tree, including no untracked files.
2. Adds the official `upstream` remote only if it is missing.
3. Fetches `origin` and `upstream`.
4. Switches to the selected local custom branch.
5. Fast-forwards it from the matching `origin/<branch>`.
6. Detects the official upstream default branch.
7. Creates a local backup branch named like
   `backup/loomx-before-upstream-2026-07-30_031500`.
8. Merges `upstream/<default-branch>` without rewriting history.
9. Builds the Loomx UI overlay and selected firmware environment.
10. Packages and checksums the firmware.
11. Pushes the custom branch only after the build succeeds.
12. Uploads only a non-empty, successfully built binary.

The official WLED default branch may be a development branch. This script
intentionally follows it because it is designed to pull the latest official
source. The existing scheduled Loomx workflow can continue to be used when
only stable WLED release tags are desired.

Inspect remotes at any time:

```bash
git remote -v
git remote show upstream
```

If `upstream` is missing, the script adds:

```bash
git remote add upstream https://github.com/Aircoookie/WLED.git
```

It warns and preserves the configuration when an existing `upstream` points
somewhere unrecognized.

## PlatformIO environment selection

Select the target in one of three ways, highest priority first:

```bash
scripts/update-build-deploy-wled.sh --env esp32dev
```

```bash
WLED_PIO_ENV=esp32dev scripts/update-build-deploy-wled.sh
```

```bash
# .env.wled-deploy
WLED_PIO_ENV=esp32dev
```

When no target is supplied, the script uses `esp32dev` only after confirming
that it exists in the effective PlatformIO configuration. It stops before any
Git mutation if the requested environment is invalid.

List the effective environments:

```bash
pio project config --json-output
```

## Running the workflow

Review the plan without changing anything:

```bash
scripts/update-build-deploy-wled.sh --dry-run
```

Run the complete merge, build, push, and upload:

```bash
scripts/update-build-deploy-wled.sh
```

Build without pushing:

```bash
scripts/update-build-deploy-wled.sh --no-push
```

Build without uploading:

```bash
scripts/update-build-deploy-wled.sh --no-upload
```

Build without either external operation:

```bash
scripts/update-build-deploy-wled.sh --no-push --no-upload
```

Build the current custom branch without merging upstream:

```bash
scripts/update-build-deploy-wled.sh --skip-merge --no-push --no-upload
```

Use another custom branch or target:

```bash
scripts/update-build-deploy-wled.sh \
  --branch loomx \
  --env esp32dev \
  --no-upload
```

Show all options:

```bash
scripts/update-build-deploy-wled.sh --help
```

## Merge conflicts

The script stops immediately when the upstream merge conflicts. It preserves
the merge state and prints every conflicted file. It does not build, push, or
upload.

Inspect and resolve the conflict:

```bash
git status
git diff --name-only --diff-filter=U
# Edit each conflicted file.
git add <resolved-files>
git commit
```

Then rerun with `--skip-merge` to build the resolved merge without attempting
the same merge again:

```bash
scripts/update-build-deploy-wled.sh --skip-merge
```

To abandon the merge:

```bash
git merge --abort
```

The pre-merge backup branch remains available for comparison or recovery:

```bash
git branch --list 'backup/*'
```

## Release files and manifest

Successful builds are stored under the ignored `releases/` directory:

```text
releases/
├── loomx-wled-esp32dev-2026-07-30_031500-a1b2c3d4.bin
├── loomx-wled-esp32dev-2026-07-30_031500-a1b2c3d4.bin.sha256
└── manifest.json
```

The checksum file uses the standard `SHA256  filename` format. The JSON
manifest contains:

- firmware filename and file size;
- SHA-256 checksum;
- PlatformIO environment;
- custom-branch Git commit;
- merged upstream commit;
- UTC build timestamp;
- custom branch;
- deployment status;
- remote path, when uploaded.

PlatformIO's original binary remains at:

```text
.pio/build/<environment>/firmware.bin
```

## Local MCP configuration

MCP server URLs, project references, and authentication belong in the user's
local Codex configuration and are not stored in this repository. The `.codex/`
directory is ignored to prevent local MCP configuration from being committed.

## Validation

Run the local checks:

```bash
bash -n scripts/update-build-deploy-wled.sh
shellcheck scripts/update-build-deploy-wled.sh
scripts/update-build-deploy-wled.sh --help
scripts/update-build-deploy-wled.sh --dry-run --no-push --no-upload
codex mcp get supabase
git check-ignore -v .env.wled-deploy releases/test.bin
```

No upload is performed by these commands.
