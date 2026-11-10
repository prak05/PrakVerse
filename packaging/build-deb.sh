#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -n 1)
ARCH=$(dpkg --print-architecture)
PACKAGE="prakverse_${VERSION}_${ARCH}"
STAGE="$ROOT/build/$PACKAGE"

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/prakverse/prakverse" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/icons/hicolor/scalable/apps"

cp -R "$ROOT/src/prakverse/." "$STAGE/usr/share/prakverse/prakverse/"
find "$STAGE/usr/share/prakverse/prakverse" -type d -name __pycache__ -prune -exec rm -rf {} +
cp "$ROOT/intel_projects.json" "$STAGE/usr/share/prakverse/intel_projects.json"
cp "$ROOT/packaging/prak" "$STAGE/usr/bin/prak"
cp "$ROOT/packaging/prakverse-app" "$STAGE/usr/bin/prakverse-app"
cp "$ROOT/packaging/prakverse-app" "$STAGE/usr/bin/prakverse"
cp "$ROOT/packaging/prakverse-app" "$STAGE/usr/bin/prak-verse"
cp "$ROOT/packaging/prakverse.desktop" "$STAGE/usr/share/applications/prakverse.desktop"
cp "$ROOT/src/prakverse/web_assets/icon.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/prakverse.svg"
chmod 0755 "$STAGE/usr/bin/prak" "$STAGE/usr/bin/prakverse-app" "$STAGE/usr/bin/prakverse" "$STAGE/usr/bin/prak-verse"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: prakverse
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Prakhar Sharma <prak05@users.noreply.github.com>
Depends: python3 (>= 3.11), python3-tk, curl
Description: PrakVerse local intelligence assistant
 Private, local-first assistant powered by Priyumvada.
 Includes the desktop interface, CLI, Central Intel, and voice-ready controls.
EOF

mkdir -p "$ROOT/dist"
dpkg-deb --build --root-owner-group "$STAGE" "$ROOT/dist/$PACKAGE.deb"
printf '%s\n' "$ROOT/dist/$PACKAGE.deb"
