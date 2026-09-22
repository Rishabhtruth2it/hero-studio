#!/bin/bash
# Build / refresh the ONE Hero Studio.app at /Applications/Hero Studio.app.
# Assembles in a temp dir — never leaves a bundle inside the project — and
# removes any stray copies so exactly one Hero Studio app exists on the system.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="Hero Studio"
DEST="/Applications/$NAME.app"
[ -w "/Applications" ] || DEST="$HOME/Applications/$NAME.app"

echo "project : $HERE"
echo "target  : $DEST"

STAGE="$(mktemp -d)/$NAME.app"
mkdir -p "$STAGE/Contents/MacOS" "$STAGE/Contents/Resources"
cp "$HERE/desktop/Info.plist" "$STAGE/Contents/Info.plist"
sed -e "s|@@PROJECT_DIR@@|$HERE|g" \
  "$HERE/desktop/launcher.sh" > "$STAGE/Contents/MacOS/$NAME"
chmod +x "$STAGE/Contents/MacOS/$NAME"

if [ -f "$HERE/desktop/hero-studio-1024.png" ]; then
  ISET="$(mktemp -d)/hero-studio.iconset"; mkdir -p "$ISET"
  for s in 16 32 128 256 512; do
    sips -z "$s" "$s" "$HERE/desktop/hero-studio-1024.png" --out "$ISET/icon_${s}x${s}.png" >/dev/null
    sips -z "$((s*2))" "$((s*2))" "$HERE/desktop/hero-studio-1024.png" --out "$ISET/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$ISET" -o "$STAGE/Contents/Resources/hero-studio.icns"
  rm -rf "$(dirname "$ISET")"
fi

for stray in "/Applications/$NAME.app" "$HOME/Applications/$NAME.app"; do
  [ -e "$stray" ] && { rm -rf "$stray"; echo "removed old: $stray"; }
done
mkdir -p "$(dirname "$DEST")"
cp -R "$STAGE" "$DEST"
rm -rf "$(dirname "$STAGE")"
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
touch "$DEST"

echo
echo "one app installed: $DEST"
echo "  (re-run this script any time to refresh it in place)"
