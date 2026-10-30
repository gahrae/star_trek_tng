#!/usr/bin/env bash
# Rebuild everything: fetch what is missing, regenerate notes and site, then run the checks.
#   ./build.sh            notes + site + checks (fetchers skip anything already on disk)
#   ./build.sh --fetch    also refetch Wikipedia credits (transcripts, cast and images are cached)
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${1:-}" == "--fetch" ]]; then
  python3 -I scripts/fetch_transcripts.py
  python3 -I scripts/fetch_metadata.py
  python3 -I scripts/fetch_cast.py
  python3 -I scripts/fetch_images.py
  python3 -I scripts/fetch_episode_images.py
fi
rm -f notes/characters/*.md notes/episodes/*.md notes/locations/*.md
python3 -I scripts/build_notes.py
python3 scripts/build_site.py
python3 -I scripts/check.py
