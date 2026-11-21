#!/usr/bin/env bash
# Đóng gói bản phát hành từ commit đang checkout: bash tools/package.sh v1.0.0 -> dist/quan-an-cho-noi-v1.0.0.zip
set -euo pipefail
V="${1:-v1.0.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/dist"
git -C "$ROOT" archive --format=zip --prefix="quan-an-cho-noi-$V/" -o "$ROOT/dist/quan-an-cho-noi-$V.zip" HEAD
echo "$ROOT/dist/quan-an-cho-noi-$V.zip"
