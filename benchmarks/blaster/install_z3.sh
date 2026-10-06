#!/usr/bin/env bash
# Install the pinned Z3 release used by the Blaster baseline harness into
# <repo>/.tools/z3-<version>/ (gitignored). The archive is verified against the
# sha256 published on the GitHub release; any mismatch aborts.
set -euo pipefail

Z3_VERSION="4.15.2"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$REPO_ROOT/.tools/z3-$Z3_VERSION"
BASE_URL="https://github.com/Z3Prover/z3/releases/download/z3-$Z3_VERSION"

case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)  ASSET="z3-$Z3_VERSION-arm64-osx-13.7.6.zip"
                   SHA256="fdc797b046a8b1e030200d30c4c32724fc01be359c3ab88a47ce03655cf6efa4" ;;
    Darwin-x86_64) ASSET="z3-$Z3_VERSION-x64-osx-13.7.6.zip"
                   SHA256="2c0fb34703660cb3c182c84d702674f52b56f9454cdc6c30d58611a1c2d69851" ;;
    Linux-x86_64)  ASSET="z3-$Z3_VERSION-x64-glibc-2.39.zip"
                   SHA256="85d2da1bf440fca3288874c2a06e23f96d09befcc21b5a7489fe0fa40444e685" ;;
    Linux-aarch64) ASSET="z3-$Z3_VERSION-arm64-glibc-2.34.zip"
                   SHA256="13ef5c1f91cae46c3de493cd1f98954331e4e7d0850bbbcf208b818d452bf99b" ;;
    *) echo "install_z3: unsupported platform $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

if [[ -x "$DEST/bin/z3" ]] && "$DEST/bin/z3" -version | grep -qx "Z3 version $Z3_VERSION - 64 bit"; then
    echo "Z3 $Z3_VERSION already installed at $DEST/bin/z3"
    exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading $ASSET ..."
curl -fsSL -o "$tmp/$ASSET" "$BASE_URL/$ASSET"

actual="$(shasum -a 256 "$tmp/$ASSET" 2>/dev/null || sha256sum "$tmp/$ASSET")"
actual="${actual%% *}"
if [[ "$actual" != "$SHA256" ]]; then
    echo "install_z3: sha256 mismatch for $ASSET" >&2
    echo "  expected $SHA256" >&2
    echo "  actual   $actual" >&2
    exit 1
fi

unzip -q "$tmp/$ASSET" -d "$tmp/x"
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$tmp/x/${ASSET%.zip}" "$DEST"

"$DEST/bin/z3" -version
echo "Installed Z3 $Z3_VERSION at $DEST/bin/z3"
