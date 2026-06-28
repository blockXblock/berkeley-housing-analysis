# Multi-Drive Audit — 2026-05-30

Read-only audit of 4 external drives. Stages 2–5 (Stage 1 enumeration was
done in the prior session). Time-boxed to 60 min. JG2TB (corrupt) probed
light-touch only (depth ≤2, no `du`).

All sizes are `du -sh` (on-disk) except JG2TB, which is inferred from `df`
and depth-2 listing only.

---

## Stage 2 — Per-drive characterization

| Drive | Hardware | FS | Size | Used | Free | Era / purpose |
|---|---|---|---|---|---|---|
| **T7** | Samsung PSSD T7 (SSD) | exFAT (128 KB cluster) | 1.0 TB | 827 GiB | 104 GiB | **Active** portable working/archive drive |
| **Seagate "JG 2016"** | Seagate BUP Slim RD | HFS+ | 2.0 TB | 423 GiB | 1.4 TiB | 2016 backup → 2020 Big Sur migration staging |
| **WD "JG2TB"** | WD My Passport | HFS+ (**corrupt, RO**) | 2.0 TB | 1.7 TiB | 99 GiB | Time Machine backup, 2013–2022 |
| **Toshiba "Data"** | Toshiba EXTERNAL_USB | exFAT | 4.0 TB | 407 GiB | 3.2 TiB | 2022 home snapshot + 2024 Acronis image |

None expose SMART over their USB bridges (normal — not a health signal).
The Toshiba also carries a tiny `Acronis Bootable Media` partition (4.2 GB).

### Per-drive top-level

- **T7** (active): `JBook-archive-2026-05-30` (15G), `Projects-archive-2026-05-30`
  (23G), `Photos Library.photoslibrary` (36G), `Videos` (8.5G),
  `berkeley-data-snapshot-2026-05-30` (3.4G), `JG-2016/` (**535G** — see below),
  plus media (`Omar-Yaghi-2.MOV` 3G, `ObamaVictorySpeechIowa.wav` 177M) and
  many small project folders (BeahrsELP, California-Africa, Obama, WNJ, etc).
  `JG 2016` (file) is a **Finder alias** pointing at the Seagate volume — not data.
- **Seagate**: `New Folder With Items` (**387G**), `macOS Install Data` (7.4G),
  `MailBackup.0408` (1G), `Backup Mail`, `BigSur`, `Recovered Nov2020`.
- **WD JG2TB**: `Backups.backupdb` (Time Machine: `JGAir11` 2018, `John's
  MacBook Air` 2020), `New Folder With Items`, `tmbootpicker.efi`. Corrupt FS.
- **Toshiba**: `John's MacBook Air.tibx` (**180G** Acronis image, May 2024),
  `Desktop` (87G), `Pictures` (38G), `Documents` (19G), `Audiobooks` (87G),
  `Downloads` (7G), `Zotero` (146M), `JG2016/` (empty, 256K).

---

## Stage 3 — Redundancy + independent collections

### The "JG2016" naming knot — resolved

Four similarly-named items, treated as independent per instruction:

1. **Seagate volume "JG 2016"** — the physical 2TB backup drive (bought 2016).
2. **T7 `JG 2016`** (file) — a MacOS **alias** to the Seagate volume. Cosmetic.
3. **T7 `JG-2016/`** (folder) — contains only a copy of `New Folder With Items`.
4. **Toshiba `JG2016/`** (folder) — contains only an **empty** `New Folder With
   Items` (an aborted copy, dated Oct 1 2025).

### Seagate "JG 2016" collection (independent characterization)

- **Size/count**: 423 GiB used; bulk is the 387G `New Folder With Items` archive.
- **Date range**: 2002–2021, **concentrated 2018–2020**; secondary clusters 2011, 2016.
- **File types** (sampled): `js` (588), `pdf` (217), `jpg` (130), `mov` (74),
  `png` (56), `doc` (34), `html` (28), `mp4` (24) — a blend of **web/dev code**
  (js/css/html/json, Docker, VMs), **documents**, and **photo/video media**.
- **Signature dirs**: `reading list from sasha` (141 items, 2016), `Classes`,
  `Books`, `FromBlack`, `DockerContainer`, `VirtualMachine`, `Movies`,
  `Pictures`, `MobileSync` (iOS backups, 2013), `Recovered Nov2020`.
- **What it is**: a long-tail personal/work archive that accreted onto a 2016
  backup drive and got swept up in a Nov 2020 Big Sur migration.

### T7 "JG-2016" collection (independent characterization)

- **Size/count**: single folder, `New Folder With Items` = **535G** on-disk.
- **Content**: byte-for-byte the **same** 16 subdirs as the Seagate archive
  (identical `.DS_Store` size 22532, identical dir names and dates).
- **Why 535G vs Seagate's 387G**: not more data — T7's exFAT uses a 128 KB
  allocation block vs HFS+'s 4 KB, inflating on-disk size for many small files.
- **What it is**: a **redundant copy** of the Seagate archive sitting on the
  active SSD. Independent in name only; content is the Seagate collection.

### Redundancy findings (cross-drive, where applicable)

| # | What | Where | Verdict |
|---|---|---|---|
| R1 | `New Folder With Items` archive | Seagate (387G, **original**) + T7 (535G copy) + Toshiba (empty) | **T7 copy is redundant** — consumes >½ the active SSD |
| R2 | Backup generations | WD TM (2018–20), Toshiba home-snapshot (Oct 2022), Toshiba Acronis (May 2024) | 3 eras/systems; overlapping personal content (Pictures, Documents recur) — **consolidate, don't delete blindly** |
| R3 | Internal ↔ T7 archives | `JBook-archive`, `Projects-archive` | **Intentional & verified** — keep |

---

## Stage 4 — Reorganization proposal

Disk pressure is resolved (internal now 57 GiB free / 73%), so nothing here is
urgent. Priorities ordered by payoff. **All deletes follow the verified pattern:
confirm checksums/counts, then delete — and only after your explicit OK.**

**P1 — Reclaim ~535G on the active T7 by removing the redundant archive copy.**
The `T7:/JG-2016/New Folder With Items` (535G) duplicates `Seagate:/New Folder
With Items` (387G), which lives on a healthy drive with 1.4 TiB free.
- *Before deleting*: verify the Seagate original is complete and readable
  (count + size + spot-checksum a sample against the T7 copy).
- *Then*: drop the T7 copy. Recovers >half the SSD for live work.
- Also delete the empty `Toshiba:/JG2016/` and the cosmetic `T7:/JG 2016` alias.

**P2 — Rescue the corrupt WD JG2TB before it degrades further.**
1.7 TiB of Time Machine history on an unrepairable filesystem. Don't trust it.
If anything on it is unique (TM history not captured elsewhere), copy the
needed slices off to the Toshiba (3.2 TiB free) *now*, light-touch, then retire
the drive. This is the only drive with a real failure risk.

**P3 — Consolidate backup generations onto the Toshiba (4TB, 3.2 TiB free).**
The Toshiba is the natural archive hub: biggest, emptiest, healthy. Target
layout: one folder per backup generation (`TimeMachine-2018-2020/`,
`HomeSnapshot-2022-10/`, `AcronisImage-2024-05/`, `Archive-NFWI/`). Then the
Seagate can become free working space or a second redundant copy of what matters.

**P4 — Decide the canonical home for the NFWI archive.**
It's 2002–2021 personal history. Recommend: keep the **Seagate HFS+ original**
as canonical, make **one** redundant copy on the Toshiba, and keep it **off**
the active T7. Optionally prune within it later (old VMs, DockerContainer,
MobileSync iOS backups from 2013 are likely dead weight).

---

## Stage 5 — Summary

- **4 drives, all read-only-probed.** Healthy: T7, Seagate, Toshiba. **At risk:
  WD JG2TB** (corrupt FS, 1.7 TiB TM history).
- **Biggest win**: ~535G of the active T7 SSD is a redundant copy of the Seagate
  archive (R1). Removing it (after verification) is the single highest-payoff move.
- **Biggest risk**: WD JG2TB corruption (P2) — only drive that could lose data.
- **"JG2016" confusion is benign**: an alias + a duplicate folder + an empty
  folder, all tracing back to one Seagate archive.
- No destructive action taken. Proposals P1–P4 await your go-ahead.

*Caveats: SMART unavailable over USB (drive-health unknown for all 4). JG2TB
inventoried at depth ≤2 only — unique content there is not fully enumerated.
Year/file-type stats for the NFWI archive are from a sample, not a full walk.*
