#!/bin/bash
set -euo pipefail

UV_VERSION="0.11.28"
TORCH_VERSION="2.11.0"

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
  backend="$($python_exe -c 'import torch; print("mps" if torch.backends.mps.is_available() else "cpu")')"
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
  progress 94 "Installing DaVinci Resolve Studio integration…"
  helper="$resources_dir/install-resolve-plugin.applescript"
  plugin="$app_dir/resolve/LyricsAligner.py"
  [[ -f "$helper" && -f "$plugin" ]] || fail "Resolve integration files are missing."
  /usr/bin/osascript "$helper" "$plugin"
fi

progress 100 "Installation complete."
