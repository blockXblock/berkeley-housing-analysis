# Data request — PG&E: Berkeley pole and distribution-transformer inventory

**Status:** DRAFT, not sent. John reviews and sends.
**Date drafted:** 2026-08-30
**Send to:** `PGJointPoleAgency@pge.com` (Joint Pole Agency — the JUMP/pole-records
contact) with a copy to PG&E Local Public Affairs, East Bay Division.
**Fallback / escalation:** CPUC PRA request (see the companion draft) and, if the
City is willing to co-sign, a City-of-Berkeley-to-PG&E request under the franchise
relationship, which is a materially stronger ask than a private one.

---

## What we already hold (state this first — it makes the ask concrete)

From the City of Berkeley's public streetlight layer (`PublicWorks/PubWorks/MapServer/26`,
retrieved 2026-08-30, 7,969 records) we already hold, for city streetlights mounted on
**wood poles**:

- **4,499 wood-pole streetlight records**, of which **4,456 carry a utility pole number**
  (`UTIL_PN`) — **4,428 distinct pole IDs**, overwhelmingly in PG&E's `B####` Berkeley
  series — each with a latitude/longitude, a nearest address, and a PG&E `SAID`/`SPID`
  service-agreement and service-point ID.

We are therefore not asking PG&E to find poles for us. We are asking for **attributes on
poles we can already name**, plus the remainder of the Berkeley pole population.

## The request

For the geographic area of the City of Berkeley, Alameda County, California:

**1. Pole inventory**
   a. Pole ID / tag number, latitude and longitude, for every PG&E-owned or
      PG&E-jointly-owned distribution pole within the city limits.
   b. Ownership and joint-use status under the Northern California Joint Pole
      Agreement — designated owner, and whether AT&T or another party holds
      communications space.
   c. Pole class, height, material, install year, and last GO 165 inspection date
      and condition rating.

**2. Distribution transformer inventory — the primary ask**
   For every pole-mounted (and, separately, pad-mounted) distribution transformer
   in Berkeley:
   a. The pole ID it is mounted on (or pad location), and latitude/longitude.
   b. **Number of transformers at that location** (single unit vs. a two- or
      three-unit bank).
   c. kVA rating, phase, and primary voltage.
   d. **Manufacture year and install year** — the load-bearing field, see below.
   e. **Insulating fluid type** — mineral oil, natural/synthetic ester, silicone,
      or dry-type.
   f. **PCB status**: tested / not tested; if tested, the measured concentration
      band (<50 ppm, 50–499 ppm "PCB-Contaminated", ≥500 ppm "PCB Transformer");
      if untested, the regulatory assumption applied.
   g. Any recorded leak, spill, failure, or replacement event, with date.

**3. Berkeley system context**
   a. Overhead vs. underground distribution circuit miles within the city.
   b. Count of Berkeley poles scheduled for replacement, and transformers
      scheduled for replacement or retrofill, under the current Wildfire
      Mitigation Plan and system-hardening programs.

## Why manufacture year is the field that matters

Under **40 CFR 761.2**, any mineral-oil-filled electrical equipment manufactured
**before July 2, 1979** whose PCB concentration has not been established **must be
assumed to be PCB-Contaminated Electrical Equipment** (≥50 ppm, <500 ppm). Berkeley's
overhead distribution system is decades old. Manufacture year plus test status is
therefore sufficient to determine how many Berkeley transformers are *legally presumed*
PCB-contaminated today — which is the number this project exists to establish.

## Format and terms

- Preferred: CSV or GeoJSON, one row per pole and one row per transformer, joined
  by pole ID.
- We understand pole-location data is treated as sensitive. We are willing to
  discuss aggregation (e.g. block-face or census-block level) or a delayed release
  for any field PG&E considers security-sensitive, and we will state the
  aggregation level publicly wherever we use it.
- We will publish the methodology and cite PG&E as the source, and will publish
  PG&E's response — including a declination — in full.

## Known obstacle, to be acknowledged in the letter

The Joint Use Map Portal (JUMP), which holds exactly this pole data, is restricted
by PG&E's terms to utilities and communications infrastructure providers operating
in the service territory, plus their contracted vendors under NDA. We are not
eligible and are not asking for JUMP access; we are asking for an extract.
Separately, **CPUC D.21-10-019** created pole-attachment databases at the five major
pole owners, but that decision expressly does **not** make them public. So this is a
discretionary release by PG&E, not a compelled one — which is worth saying plainly.
