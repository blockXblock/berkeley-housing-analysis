# The 8 GB playbook — memory, swap, and Google Earth tour recording

*Consolidated 2026-09-04 from the chat record across five sessions (July 18 kernel panic;
Aug 14 swap recovery; Aug 26 Earth-wedged crisis; Aug 30 crash + recording checklist;
Sep 1–2 cache diagnosis, Movie Maker settings, and the pre-warming post-mortem). For the
workflow: prepare tours → record in Google Earth Pro Movie Maker → publish to YouTube →
berkeleybuild.com.*

---

## 1. The three hard constraints (nothing bypasses these)

1. **8 GB RAM.** Earth Pro with custom 3D geometry + a browser + Claude sessions
   exceeds it routinely. Every crisis in the record is this ceiling.
2. **Google Earth's disk cache is capped at 2,048 MB** (`Cache.DiskCacheSize`) — a hard
   application maximum, not a setting we can raise. Six corridors of Berkeley 3D don't fit,
   so **each corridor you load evicts the previous one's tiles**. Grey terrain / missing 3D
   buildings on tour load is *cache eviction*, *not* swap and *not* bandwidth (diagnosed Sep 1).
   The Sep 1 corollary — "pre-warm the cache before recording" — did **not** survive testing;
   see §5.
3. **Swap (virtual memory) is managed by macOS and bounded by free disk.** You cannot
   pre-allocate or "maximize" it; macOS grows swapfiles on demand (observed growing
   7 → 10 GB under load) **only while the boot disk has free space**. Used swap is never
   reclaimed while the holding processes live — **only a reboot empties swap**.

> ⚠ **Standing hazard measured 2026-09-04:** boot disk at **5.7 GB free** with swap already
> 6.2/7.0 GB used. Low disk = macOS can't grow swap = the July-18-style memory panic
> (compressor at 100% of limit, watchdog timeout) gets *more* likely. Keeping **≥ 20 GB free**
> on the boot disk is part of memory hygiene, not just tidiness.

## 2. What actually happened each time (the case history)

| date | symptom | real cause | fix that worked |
|---|---|---|---|
| Jul 18 | kernel panic, watchdog timeout | `mds` (Spotlight) ballooned to 21 GB indexing rescue drives; compressor 100%, 19 swapfiles | `sudo mdutil -i off /Volumes/Data /Volumes/T7-2026`; Spotlight privacy exclusions for `berkeley-data/{databases,data,scratch}` |
| Aug 14 | swap 9.0/10 GB, sluggish | 5+ idle claude-code sessions + Chrome/CIC + Claude desktop | close idle sessions/tabs → `sudo purge` → reboot (temp files in `scratch/` survive; only `/tmp` doesn't) |
| Aug 26 | Earth menus unresponsive, "night mode", stars | 65 MB free of 8 GB, 2.2 GB swap: machine paging, Earth wedged (plus its window stranded off-screen) | force-quit Earth, power-cycle, reopen minimally, layers off |
| Aug 30 | Earth crashed outright; low-res imagery "fills in late" | swap 6.5/7.2 GB full after 4 days uptime; 35M swapouts — tiles evicted as fast as they streamed | Chrome+Comet closed (2.46 GB freed), reboot, record on a clean machine |
| Sep 1 | Durant/Bancroft tours load no terrain/3D | **disk cache eviction** (2 GB ceiling full), not memory | load one corridor at a time, record immediately |
| Sep 2 | Shattuck renders kept failing; Earth crashed 19× in one night | the crashes were the **pre-warm script itself** (segfaults in Apple Event processing, driven by its polling loop). The render failures were **not** pre-warming, label volume, machine memory, or sleep — warmed Shattuck failed twice while unwarmed dormitories rendered clean | retire pre-warming from the workflow; record unwarmed |
| Sep 5 | Kennedy tour: two renders stalled, then **Movie Maker would not start at all** | **0.1 GB free RAM; the swap CEILING itself had contracted 7.0 → 4.1 GB** because the boot disk fell to 7.3 GB. Six days' uptime, load avg 12.7. Movie Maker span up a `VTEncoderXPCService` and it sat at 0.0% CPU — it could not get memory for a 1080p encoder | close Chrome (~737 MB), quit Earth, **reboot**, free boot disk |

## 3. Maximizing available memory — the pre-recording checklist

Best → least effective, from the measured sessions:

1. **Reboot first.** The only operation that empties swap and resets the swapfiles.
   After a multi-day uptime this is worth more than everything below combined.
   Nothing is lost: repo work is committed/on disk, `scratch/` survives reboots,
   Earth's tile cache is on disk and survives, Movie Maker settings persist
   (they're written on *graceful* quit — never `kill -9` Earth or you lose them).
2. **Open only Google Earth Pro + one terminal (Claude Code).** Resume with `claude --continue`.
3. **Keep the browsers closed until the take is safe.** Measured Aug 30:
   Chrome 1,253 MB + Comet 1,203 MB = **2.46 GB — more than everything else combined**.
   Claude desktop is another ~500–580 MB if more headroom is needed.
4. **Close extra claude-code sessions** — each idle session held a real chunk of RAM (Aug 14:
   five running at once). Keep the one you're using.
5. **`sudo purge`** — flushes inactive/file-cache memory for immediate (partial) relief
   mid-session when a reboot is inconvenient.
6. **Keep Spotlight off the heavy trees.** External/rescue drives:
   `sudo mdutil -i off /Volumes/<drive>`. The repo's `databases/`, `data/`, `scratch/`
   belong in System Settings → Spotlight → Search Privacy (or the
   `scratch/2026-07-18/spotlight_exclude.sh` script; the terminal needs Full Disk Access).
   A runaway `mds` caused the July 18 kernel panic.
7. **Free boot-disk space** so swap can grow (see the hazard box above). This is the
   only sense in which swap can be "maximized."
8. Monitoring one-liners:
   ```bash
   sysctl vm.swapusage          # swap total/used/free
   memory_pressure | head -5    # system pressure %
   vm_stat | head -8            # free/active/wired pages, swapins/outs
   ```
   Rules of thumb from the record: swap **> ~85 % used** → reboot before recording;
   swapouts climbing by millions → the tour will outrun its own cache.

**What does *not* help:** pre-warming the tile cache with the script (disproven Sep 2 —
see §5; it also crashed Earth 19 times); trimming `scratch/` or other files for *memory*
reasons (disk only matters via the swap-growth ceiling); raising Earth's memory cache
(`Cache.MemoryCacheSize`, 240 MB — a bigger one just competes with the system for the same
8 GB; the binding constraint is the 2 GB *disk* cache); rebooting to fix *grey terrain*
(that's cache eviction — the cache is on disk and survives reboot).

## 4. Google Earth Pro settings for recording (as settled Aug 26 – Sep 2)

- **Layers OFF: 3D Buildings, Photos, Roads, Atmosphere.** 3D Buildings is the big memory
  consumer and double-draws against our extruded geometry; Roads paints stripes on the
  pavement in low cruises; Atmosphere adds horizon haze at our near-horizontal tilt.
  Leave **Historical Images** off too.
- **Skip the ADU layer** (876 extra extruded polygons) unless it's the subject of the take.
- **Movie Maker: Custom → 1920×1080 @ 29.97 fps.** Do *not* record 2160p/4K on this
  machine — 249 M pixels/s vs 62 M is where renders stall or drop detail (the grey-terrain
  starvation, during encoding). 1080p is the right delivery size for the site.
  Settings persist across launches — set once per batch, but only a graceful quit saves them.
- Output to the mounted T7, and re-check the output path (a remembered stale
  `/Volumes/...` path fails silently).

## 5. The recording rhythm — and the death of pre-warming

**Pre-warming is retired (Sep 2).** It was the Sep 1 theory; one night of recording disproved it:

- **It didn't help.** Shattuck was warmed before **both** of its render failures; the
  dormitories tour rendered **clean with no warm at all**. Warming was at best insurance,
  and the evidence says not even that.
- **It actively hurt.** The script's polling loop (`GetStreamingProgress` over Apple Events)
  **segfaulted Earth 19 times in one night** — the crashes attributed to "memory" that night
  were the warm-up tool itself.
- Also disproven the same night, so the next session doesn't re-test them: Shattuck's
  failures were *not* label volume, *not* machine memory (the rate recovered while swap was
  higher), *not* sleep (`caffeinate` held it). The streaming write-rate is a poor health
  signal — it prompted a cancel advice that would have discarded a good render.

Why unwarmed rendering works: **Movie Maker renders frame by frame and waits for its own
tiles** — it doesn't need the cache pre-filled the way live playback does. The cache ceiling
still matters for what you *load*, not for how you prepare.

The rhythm that stands:

1. **Give the machine headroom first** (§3): reboot if swap is high, browsers closed,
   Earth + one terminal only. This is the one lever with measured effect on imagery quality —
   the Aug 30 session showed tiles being evicted from RAM as fast as they streamed
   (35 M swapouts), and footage visibly improved after a clean relaunch.
2. **One corridor at a time.** Delete the previous package from Temporary Places, load the
   next `LABELLED-*.kmz`, check the tour's build stamp (an old stamp = an old package),
   record immediately. Anything loaded in between evicts tiles.
3. **Do not run `scripts/prewarm_tour.py`** — and nothing else that drives Earth over
   AppleScript — while Earth is rendering. If a take comes out with late-filling imagery,
   the fallback is a manual play-through once, then record pass two (unproven, but benign).
4. **Restart Earth between recordings** on long batches — three days of accumulated Earth
   state was itself a crisis (65 MB resident, everything paged out).
5. Full automation of Movie Maker is **not possible** — Earth's AppleScript dictionary has
   no Movie Maker command; recording stays a manual click. (The frame-by-frame
   `MoveCamera`+`SaveScreenShot`+ffmpeg route ≈ 14,000 frames / ~4 h per tour — a last resort
   for a tour that keeps failing, and now doubly suspect since it drives the same Apple Event
   interface that crashed Earth.)
6. What needs re-recording and why: `python3 scripts/tour_staleness.py`.

## 6. Crash safety (why none of this risks work)

Everything upstream of Earth is durable: tours and geometry are generated files, committed on
`dev`; DB writes are transactional with snapshots; `scratch/` survives reboots. An Earth crash
costs a replay, never work. When Earth hangs on quit it is usually a hidden modal
("Save changes to My Places?" → **Don't Save**); a plain `kill <pid>` is a graceful quit,
`kill -9` loses the Movie Maker settings.

---

## 7. Sep 5 — the swap ceiling can shrink, and a new "wedged" signature

Added the day after this playbook was consolidated, because it predicted the failure and was
not read until the machine had already lost three renders.

**The new mechanism: the swap ceiling is not fixed, and it contracted.** §1 says macOS grows
swapfiles on demand while the boot disk has space, and the hazard box warns that low disk
prevents *growth*. What actually happened is worse — the ceiling **fell from 7.0 GB (Sep 4) to
4.1 GB (Sep 5)** as the boot disk sat at 7.3 GB free. So the headroom did not merely stop
growing; it was taken away. **Check `sysctl vm.swapusage` for the TOTAL, not just the used
figure** — a shrinking total is an early warning that reads as "plenty free" if you only look
at the ratio (2.9 of 4.1 used looks healthier than 6.2 of 7.0, and is much worse).

**A new diagnostic signature: Movie Maker that will not start.** Not a hang, not a missing
tour — the menu item does nothing. What it looks like from outside:

- Earth itself is **responsive** (`GetViewInfo` answers instantly)
- an orphaned **`VTEncoderXPCService` alive for minutes at 0.0% CPU** — Movie Maker allocated
  an encoder and never fed it
- free RAM at or under ~0.1 GB

That encoder process is the tell. It means Movie Maker *began* and could not get memory, which
is a different failure from the Aug 26 "Earth wedged" (menus unresponsive) and needs the same
fix: reboot.

**What I got wrong, so the next session does not repeat it.** §5 already records that the
streaming write-rate is a poor health signal. It is worse than "poor": this file grew in
**512 KB bursts with 4-minute gaps between them**, so a 4-minute flatline is *normal*. I called
one render dead at 7 minutes flat — it then resumed and wrote again — and had earlier called a
different one alive when it was dead. **From outside the process, at under ~20 minutes, a stall
and a pause are indistinguishable.** The Movie Maker progress bar is a better instrument than
anything measurable from the shell.

**And a monitoring trap worth naming:** a watcher that treats "no open file handle" as
*completion* is wrong, because a **deleted** file also has no handle. Mine reported "FILE
CLOSED — render finished" on a render the user had just cancelled, with an empty byte count as
the only tell. Confirm the file still exists **and** has a readable `moov` atom before calling a
render finished.

**Standing hazard, re-measured Sep 5:** boot disk **7.3 GB free of 228 GB** — a third of the
≥20 GB the checklist asks for, and now demonstrably capping swap. Freeing boot-disk space has
moved from hygiene to the binding constraint.
