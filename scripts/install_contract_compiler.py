"""Install the pinned compiler using the upstream release checksum."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import tarfile
import urllib.request
import zipfile


def install(directory):
    machine = {"AMD64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}[platform.machine()]
    target = {"Linux": "unknown-linux-gnu", "Darwin": "apple-darwin", "Windows": "pc-windows-msvc"}[platform.system()]
    suffix = "zip" if platform.system() == "Windows" else "tar.gz"
    name = f"baml-language-0.20.1-{machine}-{target}.{suffix}"
    base = "https://github.com/boundaryml/baml/releases/download/baml-language-0.20.1/"
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / name
    urllib.request.urlretrieve(base + name, archive)
    with urllib.request.urlopen(base + name + ".sha256", timeout=60) as response:
        expected = response.read().decode().split()[0]
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("compiler archive checksum mismatch")
    if suffix == "zip":
        with zipfile.ZipFile(archive) as file:
            file.extractall(directory)
    else:
        with tarfile.open(archive) as file:
            file.extractall(directory, filter="data")
    executables = list(directory.rglob("baml-cli.exe" if suffix == "zip" else "baml-cli"))
    if len(executables) != 1:
        raise ValueError("expected one compiler executable")
    result = {"path": str(executables[0].resolve()), "archive_sha256": actual, "version": "0.20.1"}
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a") as file:
            file.write(f"BAML_CLI={result['path']}\nJEVDRILL_PLATFORM={platform.system()}\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.directory)))
