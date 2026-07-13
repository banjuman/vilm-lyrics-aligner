#!/bin/bash
set -euo pipefail

configuration="${1:-Release}"
script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
desktop_project="$project_root/desktop/VilmLyricsAligner.Desktop/VilmLyricsAligner.Desktop.csproj"
build_root="$script_dir/build"
publish_dir="$build_root/publish"
payload_dir="$build_root/payload"
bundle="$build_root/Vilm Lyrics Aligner.app"
contents="$bundle/Contents"
macos_dir="$contents/MacOS"
resources_dir="$contents/Resources"
dist_dir="$script_dir/dist"
icon_source="$project_root/desktop/VilmLyricsAligner.Desktop/Assets/vilm-1024.png"
iconset="$build_root/vilm.iconset"
dmg_stage="$build_root/dmg"
dmg="$dist_dir/VilmLyricsAligner-1.0.0-apple-silicon.dmg"

[[ "$(uname -s)" == "Darwin" ]] || { echo "Run this script on macOS." >&2; exit 1; }
[[ "$(uname -m)" == "arm64" ]] || { echo "This build is Apple silicon only." >&2; exit 1; }
command -v dotnet >/dev/null || { echo ".NET 8 SDK is required to build the app." >&2; exit 1; }

rm -rf "$build_root" "$dist_dir"
mkdir -p "$publish_dir" "$payload_dir" "$macos_dir" "$resources_dir" "$dist_dir" "$iconset"

echo "Publishing Apple silicon desktop app…"
dotnet publish "$desktop_project" \
  -c "$configuration" \
  -r osx-arm64 \
  --self-contained true \
  -p:PublishSingleFile=false \
  -p:IncludeNativeLibrariesForSelfExtract=false \
  -o "$publish_dir"
cp -R "$publish_dir/." "$macos_dir/"
chmod +x "$macos_dir/VilmLyricsAligner"

echo "Preparing the private runtime payload…"
cp -R "$project_root/lyrics_aligner" "$payload_dir/"
find "$payload_dir/lyrics_aligner" -type d -name __pycache__ -prune -exec rm -rf {} +
rm -f \
  "$payload_dir/lyrics_aligner/backends/qwen.py" \
  "$payload_dir/lyrics_aligner/backends/demucs_torchaudio_legacy.py"
mkdir -p "$payload_dir/resolve"
cp "$project_root/resolve/LyricsAligner.py" "$payload_dir/resolve/LyricsAligner.py"
cp "$project_root/pyproject.toml" "$payload_dir/pyproject.toml"
cp "$project_root/LICENSE" "$resources_dir/LICENSE"
cp "$project_root/THIRD_PARTY_NOTICES.md" "$resources_dir/THIRD_PARTY_NOTICES.md"
cp "$project_root/TRADEMARKS.md" "$resources_dir/TRADEMARKS.md"
cp "$project_root/installer/requirements-app.txt" "$payload_dir/requirements-app.txt"
cp -R "$payload_dir" "$resources_dir/payload"
cp "$script_dir/install-runtime.sh" "$resources_dir/install-runtime.sh"
cp "$script_dir/install-resolve-plugin.applescript" "$resources_dir/install-resolve-plugin.applescript"
chmod +x "$resources_dir/install-runtime.sh"

echo "Creating the macOS icon…"
for size in 16 32 128 256 512; do
  /usr/bin/sips -z "$size" "$size" "$icon_source" --out "$iconset/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  /usr/bin/sips -z "$double" "$double" "$icon_source" --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
/usr/bin/iconutil -c icns "$iconset" -o "$resources_dir/vilm.icns"
cp "$script_dir/Info.plist" "$contents/Info.plist"

if [[ -n "${APPLE_SIGN_IDENTITY:-}" ]]; then
  echo "Signing with Developer ID…"
  while IFS= read -r binary; do
    /usr/bin/codesign --force --timestamp --options runtime --sign "$APPLE_SIGN_IDENTITY" "$binary"
  done < <(find "$macos_dir" -type f \( -name '*.dylib' -o -perm -111 \))
  /usr/bin/codesign --force --timestamp --options runtime \
    --entitlements "$script_dir/entitlements.plist" \
    --sign "$APPLE_SIGN_IDENTITY" "$bundle"
else
  echo "Creating an ad-hoc signed development build…"
  /usr/bin/codesign --force --deep --sign - "$bundle"
fi

/usr/bin/codesign --verify --deep --strict --verbose=2 "$bundle"

echo "Creating DMG…"
mkdir -p "$dmg_stage"
cp -R "$bundle" "$dmg_stage/"
ln -s /Applications "$dmg_stage/Applications"
/usr/bin/hdiutil create -volname "Vilm Lyrics Aligner" -srcfolder "$dmg_stage" \
  -ov -format UDZO "$dmg"

if [[ -n "${APPLE_SIGN_IDENTITY:-}" ]]; then
  /usr/bin/codesign --force --timestamp --sign "$APPLE_SIGN_IDENTITY" "$dmg"
fi

if [[ -n "${APPLE_ID:-}" && -n "${APPLE_TEAM_ID:-}" && -n "${APPLE_APP_PASSWORD:-}" ]]; then
  echo "Submitting DMG for notarization…"
  /usr/bin/xcrun notarytool submit "$dmg" --wait \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD"
  /usr/bin/xcrun stapler staple "$dmg"
fi

echo "Built: $dmg"
