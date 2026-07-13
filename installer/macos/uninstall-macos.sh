#!/bin/bash
set -euo pipefail

app_root="$HOME/Library/Application Support/Vilm Lyrics Aligner"
plugin="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/Vilm Lyrics Aligner.py"

case "$app_root" in
  *"/Library/Application Support/Vilm Lyrics Aligner") ;;
  *) echo "Unexpected application data path; uninstall stopped." >&2; exit 1 ;;
esac

rm -rf "$app_root"

app_bundle="/Applications/Vilm Lyrics Aligner.app"
if [[ -d "$app_bundle" || -f "$plugin" ]]; then
  /usr/bin/osascript - "$app_bundle" "$plugin" <<'APPLESCRIPT'
on run argv
  set appPath to item 1 of argv
  set pluginPath to item 2 of argv
  set commandText to "/bin/rm -rf " & quoted form of appPath & " && /bin/rm -f " & quoted form of pluginPath
  do shell script commandText with administrator privileges
end run
APPLESCRIPT
fi

echo "Vilm Lyrics Aligner was removed."
