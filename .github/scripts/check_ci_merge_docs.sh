#!/usr/bin/env bash
# Validate formatting and offline repository links for a verified diff.
set -euo pipefail

base="$1"
merge="$2"
scope="$3"
git diff --check "$base" "$merge"

archive="$RUNNER_TEMP/lychee.tar.gz"
curl --fail --silent --show-error --location --retry 2 \
  https://github.com/lycheeverse/lychee/releases/download/lychee-v0.24.2/lychee-x86_64-unknown-linux-gnu.tar.gz \
  --output "$archive"
echo "1f4e0ef7f6554a6ed33dd7ac144fb2e1bbed98598e7af973042fc5cd43951c9a  $archive" | sha256sum --check --strict
tar --no-same-owner -xzf "$archive" -C "$RUNNER_TEMP" --strip-components=1 lychee-x86_64-unknown-linux-gnu/lychee
python3 -I -B -c 'import json, sys; print(*json.load(open(sys.argv[1]))["paths"], sep="\n")' \
  "$scope" > "$RUNNER_TEMP/merge-docs.txt"
"$RUNNER_TEMP/lychee" --offline --no-progress --include-fragments \
  --root-dir "$GITHUB_WORKSPACE" --files-from "$RUNNER_TEMP/merge-docs.txt"
