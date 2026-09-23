#!/usr/bin/env python3
"""Fetch every published Corridors Zoning Update document into data/raw/czu/.

All of these are published by the City on the CZU page. Downloads are paced and skipped if
already present, so re-running is cheap. Writes a manifest with sizes and SHA-256 so a later
session can tell whether the City has revised a document in place -- which they do.

Usage: python3 scripts/fetch_czu_documents.py
"""
import hashlib, json, os, time, urllib.request

BASE = "https://berkeleyca.gov"
OUT  = "data/raw/czu"
UA   = {"User-Agent": "berkeleybuild-research/1.0 (+https://berkeleybuild.com)"}

DOCS = [
  # (meeting/date, label, path)
  ("2025-05-01_workshop1", "presentation",      "/sites/default/files/documents/Community%20Workshop%20%231%20Presentation.pdf"),
  ("2025-05-01_workshop1", "summary",           "/sites/default/files/documents/Berkeley%20Corridors%20Zoning%20Update_Workshop%20%231%20Summary_0.pdf"),
  ("2025-08-20_workshop2", "north_shattuck",    "/sites/default/files/documents/COMMUNITY%20WORKSHOP%202%20PRESENTATION_1.pdf"),
  ("2025-08-20_workshop2", "college_ave",       "/sites/default/files/documents/Berkeley%20Corridors%20Workshop%202%20Presentation%20-%20College_2.pdf"),
  ("2025-08-20_workshop2", "solano",            "/sites/default/files/documents/Berkeley%20Corridors%20Workshop%202%20Presentation%20-%20Solano_0.pdf"),
  ("2025-08-20_workshop2", "summary",           "/sites/default/files/documents/Berkeley%20Corridors%20Workshop%20%232%20Summary.pdf"),
  ("2025-08-20_workshop2", "boards",            "/sites/default/files/documents/BerkeleyCorridors_Workshop%202_Boards_1.pdf"),
  ("2025-09-17_pc1",       "staff_report",      "/sites/default/files/documents/Corridors%20PC_Staff%20Report.pdf"),
  ("2025-09-17_pc1",       "minutes",           "/sites/default/files/documents/Corridors_PC_meetingMinutes_0.pdf"),
  ("2025-09-17_pc1",       "presentation",      "/sites/default/files/documents/Corridors_PC_Presentation.pdf"),
  ("2025-09-20_popup",     "summary",           "/sites/default/files/documents/Berkeley%20Corridors_Pop%20Up%20Summary_Final_0.pdf"),
  ("2025-10-10_survey",    "results",           "/sites/default/files/documents/BerkeleyCorridors_SurveyResults_Final_0.pdf"),
  ("2025-11-06_council",   "presentation",      "/sites/default/files/documents/BerkeleyCorridors_CC_WS_11.6_0.pdf"),
  ("2026-02-04_pc2",       "agenda",            "/sites/default/files/2026-02/2026-02-04%20PC%20Agenda.pdf"),
  ("2026-02-04_pc2",       "minutes",           "/sites/default/files/2026-02/2026-02-04%20PC%20DRAFT%20Minutes.pdf"),
  ("2026-02-04_pc2",       "presentations",     "/sites/default/files/2026-02/PresentationsCombined_IntroSmallBusinessODS.pdf"),
  ("2026-02-04_pc2",       "late_corr_1",       "/sites/default/files/2026-02/Late%20Correspondence.pdf"),
  ("2026-02-04_pc2",       "late_corr_2",       "/sites/default/files/2026-02/2026-02-04_PC_Late%20Correspondence%202.pdf"),
  ("2026-03-04_pc3",       "agenda",            "/sites/default/files/2026-03/2026-03-04%20Agenda.pdf"),
  ("2026-03-04_pc3",       "minutes",           "/sites/default/files/2026-03/2026-03-04_PC_DRAFT%20Minutes.pdf"),
  ("2026-03-04_pc3",       "adhoc_supplemental","/sites/default/files/2026-03/2026-03-04%20Supplemental%20Agenda%20Packet.pdf"),
  ("2026-03-04_pc3",       "late_corr_1",       "/sites/default/files/2026-03/Late%20Correspondence_1.pdf"),
  ("2026-03-04_pc3",       "late_corr_2",       "/sites/default/files/2026-03/2026-03-04_PC_Item%2012_Late%20Correspondence%20Packet%202.pdf"),
  ("2026-05-06_pc4",       "staff_presentation","/sites/default/files/2026-05/StaffPresentation_PC_5.6.pdf"),
  ("2026-05-06_pc4",       "staff_report",      "/sites/default/files/2026-04/2026-05_06_PC_Item%2010A_Corridors.pdf"),
  ("reference",            "existing_conditions","/sites/default/files/documents/Corridors%20_Existing_Conditions_Report_3.5.25.pdf"),
  ("reference",            "alternatives_report","/sites/default/files/documents/08.18.2025_BerkeleyCorridors__Alternatives_Report.pdf"),
]

def main():
    os.makedirs(OUT, exist_ok=True)
    man, ok, skip, fail = [], 0, 0, 0
    for meeting, label, path in DOCS:
        dest = os.path.join(OUT, f"{meeting}__{label}.pdf")
        if os.path.exists(dest) and os.path.getsize(dest) > 2000:
            skip += 1
        else:
            try:
                req = urllib.request.Request(BASE + path, headers=UA)
                data = urllib.request.urlopen(req, timeout=60).read()
                if len(data) < 2000 or not data[:5].startswith(b"%PDF"):
                    raise ValueError(f"not a pdf ({len(data)} bytes)")
                open(dest, "wb").write(data)
                ok += 1
                time.sleep(1.0)
            except Exception as e:
                print(f"  FAIL {meeting}/{label}: {e}")
                fail += 1
                continue
        blob = open(dest, "rb").read()
        man.append({"meeting": meeting, "label": label, "file": os.path.basename(dest),
                    "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()[:16],
                    "url": BASE + path})
    json.dump(man, open(f"{OUT}/manifest.json", "w"), indent=1)
    print(f"\ndownloaded {ok}, already had {skip}, failed {fail}")
    print(f"  {len(man)} documents, {sum(m['bytes'] for m in man)/1048576:.1f} MB -> {OUT}/")

if __name__ == "__main__":
    main()
