# Star Trek: The Next Generation notes

Built from 176 episode transcripts (fan transcriptions from Chrissie's Transcripts Site, chakoteya.net, downloaded for personal study), episode credits from Wikipedia, and curated synopses, arc tags, continuity links and character profiles from the data modules in `scripts/`.

## Start here

- [episodes.md](episodes.md): every episode by season with code, airdate, director, writer, arcs and a one-line synopsis.
- [character_index.md](character_index.md): 203 characters with species, affiliation and status, linked to individual notes.
- [arcs.md](arcs.md): episodes grouped by storyline or theme (Borg, Klingon politics, Q, Data's humanity, and so on).
- [continuity.md](continuity.md): which episodes pick up threads from earlier ones.
- [relationships.md](relationships.md): curated relationships plus the most frequent scene pairings.
- [co_appearance.md](co_appearance.md): scene and episode co-appearance matrices for the main cast.
- [locations.md](locations.md): most used sets, by season, with a page per major location under `locations/`.
- [entities.md](entities.md): mention counts for recurring ships, places, factions and technology.
- [stats.md](stats.md): dialogue per character per season, catchphrase counts, longest and shortest episodes.
- [actors.md](actors.md): actors with multiple roles or many episodes, from Memory Alpha cast lists.
- [crew.md](crew.md): directors and writers, their episode counts, seasons, favourite arcs and pairings.

## Per-item notes

- `episodes/<prod>.md`: metadata, synopsis, continuity, every log entry, speaking characters with line counts, and scene locations.
- `characters/<slug>.md`: profile, key facts, rank timeline, relationships, most shared scenes, lines per season, full appearance list.

## Identifiers

Episodes are identified on the pages by their code (S03E15, broadcast order) and overall episode number. Two-part stories with a single transcript carry a code range (S01E01-E02). The studio production number (e.g. 163) is used only as the file name for transcripts, data and notes.

## Caveats

- Appearance counts are based on dialogue. For the main and recurring cast, episodes where the character is only named in stage directions are listed separately as silent appearances; this is a heuristic and can miss or over-count.
- Cast lists come from Memory Alpha (CC BY-NC) and are matched to transcript labels by name, which fails for some credits.
- Speaker labels follow the transcriber's spelling. A few aliases are merged (Geordi, Beverly, Alyssa, and Data's personas in *Masks*).
- Synopses, arc tags, continuity links, key facts, profiles, relationships and guest descriptions were written with Claude, an AI assistant. Each episode's synopsis and arc tags were written from its full transcript. Key facts, profiles, relationships and guest descriptions were written from general knowledge of the show and then checked against Memory Alpha and the transcripts. Each continuity link was checked against both episodes' transcripts. Portraits are picked by an automated search, so a few may be wrong. Check anything you rely on.

## Rebuilding

```
python3 scripts/fetch_transcripts.py   # downloads transcripts, skips files already present
python3 scripts/fetch_metadata.py      # credits and numbering from Wikipedia
python3 scripts/fetch_cast.py          # cast lists from Memory Alpha (skips pages already saved)
python3 scripts/build_notes.py         # everything under notes/
```

The curated content (synopses, arcs, continuity notes, profiles, relationships) lives in `scripts/curated_episodes.py` and `scripts/curated_characters.py`; edit those and rebuild.
