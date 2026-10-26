Import('env')
import os
import shutil
import gzip
import json
import pathlib
import re

OUTPUT_DIR = "build_output{}".format(os.path.sep)
#OUTPUT_DIR = os.path.join("build_output")

def _get_cpp_define_value(env, define):
    define_list = [item[-1] for item in env["CPPDEFINES"] if item[0] == define]

    if define_list:
        return define_list[0]

    return None

def _create_dirs(dirs=["map", "release", "firmware"]):
    for d in dirs:
        os.makedirs(os.path.join(OUTPUT_DIR, d), exist_ok=True)

def create_release(source):
    release_name_def = _get_cpp_define_value(env, "WLED_RELEASE_NAME")
    if release_name_def:
        release_name = release_name_def.replace("\\\"", "")
        variant = env["PIOENV"]
        if variant in ("vx4", "vx8"):
            version_path = pathlib.Path(env["PROJECT_DIR"]) / "loomx" / "VERSION"
            loomx_version = version_path.read_text(encoding="utf-8").strip()
            if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", loomx_version):
                raise RuntimeError(
                    "loomx/VERSION must contain a semantic version such as 1.0.1."
                )
            firmware = pathlib.Path(source).read_bytes()
            if loomx_version.encode() not in firmware:
                raise RuntimeError(
                    f"{variant} firmware does not contain Loomx version {loomx_version}."
                )
            release_file = os.path.join(
                OUTPUT_DIR,
                "release",
                f"Loomx_WLED_{loomx_version}_{release_name}.bin",
            )
        else:
            with open("package.json", "r") as package:
                version = json.load(package)["version"]
            release_file = os.path.join(OUTPUT_DIR, "release", f"WLED_{version}_{release_name}.bin")
        release_gz_file = release_file + ".gz"
        print(f"Copying {source} to {release_file}")
        shutil.copy(source, release_file)
        bin_gzip(release_file, release_gz_file)
    else:
        variant = env["PIOENV"]
        bin_file = "{}firmware{}{}.bin".format(OUTPUT_DIR, os.path.sep, variant)
        print(f"Copying {source} to {bin_file}")
        shutil.copy(source, bin_file)

def bin_rename_copy(source, target, env):
    _create_dirs()
    variant = env["PIOENV"]
    builddir = os.path.join(env["PROJECT_BUILD_DIR"],  variant)
    source_map = os.path.join(builddir, env["PROGNAME"] + ".map")
    firmware_bin = os.path.join(builddir, env["PROGNAME"] + ".bin")

    # create string with location and file names based on variant
    map_file = "{}map{}{}.map".format(OUTPUT_DIR, os.path.sep, variant)

    if not os.path.isfile(firmware_bin):
        raise RuntimeError(f"Expected firmware binary was not generated: {firmware_bin}")
    create_release(firmware_bin)

    # copy firmware.map to map/<variant>.map
    if os.path.isfile("firmware.map"):
        print("Found linker mapfile firmware.map")
        shutil.copy("firmware.map", map_file)
    if os.path.isfile(source_map):
        print(f"Found linker mapfile {source_map}")
        shutil.copy(source_map, map_file)

def bin_gzip(source, target):
    # only create gzip for esp8266
    if not env["PIOPLATFORM"] == "espressif8266":
        return
    
    print(f"Creating gzip file {target} from {source}")
    with open(source,"rb") as fp:
        with gzip.open(target, "wb", compresslevel = 9) as f:
            shutil.copyfileobj(fp, f)

# Make the release copy an always-run default target. A post-action attached
# directly to firmware.bin is skipped when PlatformIO reuses a cached binary,
# which can leave stale or missing release artifacts.
release_artifacts = env.Alias(
    "release_artifacts",
    "$BUILD_DIR/${PROGNAME}.bin",
    bin_rename_copy,
)
AlwaysBuild(release_artifacts)
Default(release_artifacts)
