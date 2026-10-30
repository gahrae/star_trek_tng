# Content and sources

This project mixes code and original work, which is open, with material collected from other sites, which is not mine to license. This file lists which is which.

*Star Trek* and all related marks and characters are the property of Paramount. This is an unofficial fan project, not affiliated with or endorsed by Paramount.

## My own work (MIT)

Covered by the MIT licence in `LICENSE`:

- `scripts/`, `build.sh`, and the site code (HTML templates, CSS, JavaScript)
- The analysis I wrote or generated for this project: synopses, arc tags, character profiles, relationship and continuity notes, and the counts and indexes computed from the transcripts (appearances, line counts, scenes, mentions, catchphrases)

Where one of those files quotes a lot of source text, the quoted text stays under the terms in the next section.

## Content from other sources (not MIT)

None of this is relicensed. It is included for study and commentary, with credit to where it came from.

| Content | Where it is | Source | Terms |
|---|---|---|---|
| Episode transcripts | `data/raw/`, `data/text/`, `site/transcripts/`, and the dialogue quoted in `notes/` and `search.json` | [Chrissie's Transcripts Site](http://www.chakoteya.net/NextGen/episodes.htm) (chakoteya.net) | The words belong to the rights holders of the show. The site owner has been told about this project and has agreed to it keeping the pages, with credit. That is permission to keep them, not a licence to reuse them. |
| Cast lists and character details | `data/ma/`, `data/cast.json` | [Memory Alpha](https://memory-alpha.fandom.com/) | CC BY-NC. Reuse needs attribution and must be non-commercial. |
| Portraits | `data/images/`, `data/images.json`, `site/images/` | Memory Alpha (the images are Paramount's) | Shown as fair use for commentary, the same way Memory Alpha does. Not relicensed. |
| Episode screenshots | `data/episode_images/`, `data/episode_images.json`, `site/episode_images/` | Memory Alpha (the images are Paramount's) | As above. |
| Episode numbering, airdates, directors, writers | `data/episodes.json`, `data/metadata.json` | Wikipedia | Facts from CC BY-SA text. Credited here. |

`data/provenance.json` records when and from where each data set was fetched.

## If you reuse anything here

- The MIT parts are free to use, with the copyright notice kept.
- For everything in the table above, go to the original source and check its terms. Do not assume the MIT licence covers it just because it is in this repository.
- Memory Alpha content carries a non-commercial condition, so a combined dataset that includes it cannot be treated as plain MIT.

## Removal requests

If you own something here and want it taken down, contact me and I will remove it promptly. Each type of content lives in its own folder with a JSON record of its source, so removal is quick. My contact details are on my GitHub profile: [gahrae](https://github.com/gahrae).
