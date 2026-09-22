---
title: "Hero loop — asset + paste-ready snippet"
date: 2026-09-22
type: note
status: for-review
area: notes
---

# Hero loop

**Asset:** `docs/videos/hero-shattuck-loop.mp4` — 17.0 s · 1280×720 · H.264 · 1.34 Mbps · **2.71 MB** · faststart · no audio
**Poster:** `docs/videos/hero-shattuck-loop.jpg` — 0.16 MB

**Source:** `/Volumes/T7-2025/Berkeley-Tours/New/1-Shattuck-S-N.m4v` (rendered 2026-09-07, the current
labelled pushpin-free geometry), seconds **214–232** — the downtown stretch where 2190 Shattuck
(452 u, In Review), 2115 Kittredge (146 u) and half a dozen further boxes are in frame at once with
Durant / Bancroft / Kittredge / Shattuck street labels.

**Loop:** seamless. The last second is a crossfade from the clip's tail back into its own head
(`xfade`, 1 s), so frame 510 ≈ frame 0 — verified by first/last frame comparison. No visible cut.

## Paste directly after `<header>` in `docs/index.html`

```html
<!-- Hero loop. Muted + playsinline so iOS autoplays inline; poster paints instantly.
     Asset: 2.71 MB, 17 s, seamless. Replaces nothing — the two 100 MB autoplaying
     mp4s at the bottom of the page should come out separately. -->
<figure id="hero" style="max-width:1000px;margin:1.5rem auto 0;padding:0 1.5rem;">
  <video id="heroVideo"
         autoplay muted loop playsinline preload="auto"
         poster="videos/hero-shattuck-loop.jpg"
         aria-label="Aerial flight north along Shattuck Avenue through downtown Berkeley. Translucent coloured blocks mark each project in the housing pipeline; 2190 Shattuck, 452 units, is labelled in the foreground."
         style="width:100%;height:auto;display:block;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,.12);background:#111;">
    <source src="videos/hero-shattuck-loop.mp4" type="video/mp4">
  </video>
  <figcaption style="margin:.6rem auto 0;text-align:center;color:#4a5568;font-size:.95rem;line-height:1.5;">
    Every coloured block is a project in Berkeley&rsquo;s housing pipeline. Warm colours are still on
    paper; cool colours exist. <a href="#tours" style="color:#1a365d;">See the corridor by corridor &rarr;</a>
  </figcaption>
</figure>
<script>
  /* Honour a reduced-motion preference: hold on the poster instead of looping. */
  (function () {
    var v = document.getElementById('heroVideo');
    if (v && window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) {
      v.removeAttribute('autoplay'); v.removeAttribute('loop'); v.pause(); v.currentTime = 0;
    }
  })();
</script>
```

## Before it ships

1. **`*.mp4` is gitignored** (`.gitignore:111`). The two existing videos are on `main`, so they were
   force-added. This one needs `git add -f docs/videos/hero-shattuck-loop.mp4` or it will silently
   fail to deploy. **Note the conflict:** `CLAUDE.md`'s media rule says repo-tracked mp4s are stale
   artifacts to delete, but the site depends on two of them. That rule and the repo disagree —
   worth settling, because the hero makes it a third.
2. **Pull the two bottom autoplays** (`campanile-adeline-shattuck.mp4` 69 MB,
   `tour-elmwood+college+bancroft+shattuck-s2n.mp4` 31 MB). Both are `needs_rerecord: true`,
   pushpin-era, and they autoplay below the fold. Net change with the hero in place:
   **99.7 MB → 2.9 MB**, a 97% cut, and the motion moves to where a new viewer sees it.
3. `#tours` anchor — the caption links to it; add `id="tours"` to the flyover section or change the href.

## Alternate encodes kept in the scratchpad
| file | size | notes |
|---|---|---|
| `h_34.mp4` | 2.71 MB | **shipped** — label text still crisp |
| `h_32.mp4` | 3.41 MB | marginally cleaner, not visibly so |
| `hero.mp4` | 4.61 MB | CRF 30 master |
| `h_960.mp4` | 2.35 MB | 960×540; only worth it if 720p proves heavy |
