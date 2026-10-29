#!/bin/sh
# Synchronizes version.json and src/version.zi with CHANGELOG.md's newest release.
set -eu
cd "$(dirname "$0")"
exec ziran run --target=c tools/update_version.zi
