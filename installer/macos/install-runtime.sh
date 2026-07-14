#!/bin/bash
set -euo pipefail

UV_VERSION="0.11.28"
TORCH_VERSION="2.11.0"
RESOLVE_PYTHON_NAME="python-3.12.10-macos11.pkg"
RESOLVE_PYTHON_SHA256="8373e58da4ea146b3eb1c1f9834f19a319440b6b679b06050b1f9ee3237aa8e4"

payload_dir="${1:?payload directory is required}"
app_root="${2:?application data directory is required}"
install_resolve="${3:-0}"
resources_dir="${4:-}"

progress() {
  printf '::progress::%s::%s\n' "$1" "$2"
}

fail() {
  printf '::error::%s\n' "$1" >&2
  exit 1
}

[[ "$(uname -s)" == "Darwin" ]] || fail "This installer only supports macOS."
[[ "$(uname -m)" == "arm64" ]] || fail "This build requires an Apple silicon Mac."

mac_major="$(sw_vers -productVersion | cut -d. -f1)"
[[ "$mac_major" -ge 14 ]] || fail "macOS 14 or later is required."
[[ -d "$payload_dir/lyrics_aligner" ]] || fail "The application payload is missing."

expected_suffix="/Library/Application Support/Vilm Lyrics Aligner"
case "$app_root" in
  *"$expected_suffix") ;;
  *) fail "Refusing to install into an unexpected directory: $app_root" ;;
esac

app_dir="$app_root/app"
tools_dir="$app_root/tools"
python_dir="$app_root/python"
venv_dir="$app_root/venv"
cache_dir="$app_root/install-cache"
models_dir="$app_root/models"
uv_archive="$cache_dir/uv-aarch64-apple-darwin.tar.gz"
uv_checksum="$uv_archive.sha256"
uv_url="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-aarch64-apple-darwin.tar.gz"

mkdir -p "$app_root" "$cache_dir" "$models_dir"
progress 4 "Preparing private application folders…"

# Keep downloaded models across repairs, but always replace executable code and
# the isolated runtime so a partially failed install cannot leak into a retry.
rm -rf "$app_dir" "$tools_dir" "$python_dir" "$venv_dir"
mkdir -p "$app_dir" "$tools_dir" "$python_dir"
cp -R "$payload_dir/." "$app_dir/"

progress 12 "Downloading the verified runtime manager…"
/usr/bin/curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
  "$uv_url" --output "$uv_archive"
/usr/bin/curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
  "$uv_url.sha256" --output "$uv_checksum"
(
  cd "$cache_dir"
  /usr/bin/shasum -a 256 -c "$(basename "$uv_checksum")"
)
/usr/bin/tar -xzf "$uv_archive" -C "$tools_dir" --strip-components=1
uv="$tools_dir/uv"
[[ -x "$uv" ]] || fail "The verified uv executable could not be extracted."

export UV_PYTHON_INSTALL_DIR="$python_dir"
export UV_CACHE_DIR="$cache_dir/uv"
export UV_NO_MODIFY_PATH=1
export LYRICS_ALIGNER_APP_ROOT="$app_root"
export XDG_CACHE_HOME="$models_dir"
export TORCH_HOME="$models_dir/torch"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTORCH_ENABLE_MPS_FALLBACK=1

progress 22 "Installing private Python 3.11…"
"$uv" python install 3.11 --install-dir "$python_dir" --no-bin
progress 30 "Creating the isolated AI environment…"
"$uv" venv "$venv_dir" --python 3.11 --managed-python
python_exe="$venv_dir/bin/python"
[[ -x "$python_exe" ]] || fail "Private Python was not created."

progress 40 "Installing PyTorch with Apple Metal support…"
"$uv" pip install --python "$python_exe" \
  "torch==$TORCH_VERSION" "torchaudio==$TORCH_VERSION"

progress 56 "Installing Vilm Lyrics Aligner components…"
"$uv" pip install --python "$python_exe" -r "$app_dir/requirements-app.txt"
"$uv" pip install --python "$python_exe" --no-deps "$app_dir"

progress 72 "Downloading AI models and checking Apple Metal…"
if "$python_exe" -m lyrics_aligner.runtime_setup; then
  backend="$("$python_exe" -c 'import torch; print("mps" if torch.backends.mps.is_available() else "cpu")')"
else
  printf 'Apple Metal validation failed; retrying with the CPU compatibility path.\n' >&2
  LYRICS_ALIGNER_DEVICE=cpu "$python_exe" -m lyrics_aligner.runtime_setup
  backend="cpu"
fi

progress 88 "Saving the private runtime configuration…"
"$python_exe" - "$app_root/config.json" "$app_dir" "$python_exe" "$backend" <<'PY'
import json
import sys
from pathlib import Path

path, project_root, python, backend = sys.argv[1:]
Path(path).write_text(
    json.dumps(
        {"project_root": project_root, "python": python, "backend": backend},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
PY

if [[ "$install_resolve" == "1" ]]; then
  helper="$resources_dir/install-resolve-plugin.applescript"
  plugin="$app_dir/resolve/LyricsAligner.py"
  resolve_python_pkg="$resources_dir/$RESOLVE_PYTHON_NAME"
  resolve_python_framework="/Library/Frameworks/Python.framework/Versions/3.12/Python"
  resolve_python_exe="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
  resolve_plugin="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/Vilm Lyrics Aligner.py"
  [[ -f "$helper" && -f "$plugin" && -f "$resolve_python_pkg" ]] \
    || fail "Resolve integration files are missing."
  actual_resolve_python_sha256="$(/usr/bin/shasum -a 256 "$resolve_python_pkg" | /usr/bin/awk '{print $1}')"
  [[ "$actual_resolve_python_sha256" == "$RESOLVE_PYTHON_SHA256" ]] \
    || fail "Resolve Python package verification failed."
  /usr/sbin/pkgutil --check-signature "$resolve_python_pkg" >/dev/null \
    || fail "Resolve Python package signature verification failed."
  if [[ -f "$resolve_python_framework" ]]; then
    progress 94 "Installing the Resolve panel; official Python.org 3.12 is already ready…"
  else
    progress 92 "Installing official Python.org 3.12 and the Resolve panel…"
  fi
  /usr/bin/osascript "$helper" "$plugin" "$resolve_python_pkg"
  progress 98 "Verifying DaVinci Resolve Studio integration…"
  [[ -f "$resolve_python_framework" && -x "$resolve_python_exe" ]] \
    || fail "Resolve Python 3.12 did not finish installing."
  /usr/bin/file "$resolve_python_framework" | /usr/bin/grep -q "arm64" \
    || fail "Resolve Python does not include Apple silicon support."
  "$resolve_python_exe" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' \
    || fail "Resolve Python 3.12 could not start."
  [[ -f "$resolve_plugin" ]] || fail "The Resolve panel was not installed."
  /usr/bin/cmp -s "$plugin" "$resolve_plugin" \
    || fail "The installed Resolve panel did not pass verification."
fi

if [[ "$install_resolve" == "1" ]]; then
  progress 100 "Setup complete. Restart Resolve before opening the Vilm panel."
else
  progress 100 "Setup complete. Vilm Lyrics Aligner is ready."
fi
