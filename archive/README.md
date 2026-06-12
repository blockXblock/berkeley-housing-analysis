# Archive — Berkeley Housing Pipeline DB consolidation

Every file here is a **verified copy** (source↔copy SHA-256 matched before the
original was removed) and is **fully recoverable**: `cp archive/<dir>/<file> <original-path>`.
Move procedure: copy → checksum-match → remove original → log. DBs stay gitignored;
this README is the tracked audit record.

## NOW batch executed 2026-06-01 (Phase 2)

| original path | archived to | sha256 | timestamp (UTC) | reason |
|---|---|---|---|---|
| databases/berkeley_v2.db | archive/retired/berkeley_v2.db | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 2026-06-01T20:11:58Z | 0-byte EMPTY orphan; no script refs |
| databases/housing_projects.db | archive/orphans/housing_projects.db | bdeeca14cff6d01f2ec883d01a2027ef3d4061c704aa8992bdd3780b7893aee2 | 2026-06-01T20:11:58Z | prototype, no script ref |
| databases/berkeley_housing_map.db | archive/orphans/berkeley_housing_map.db | d934dd100f8ad118b2fb8dc15e1679d137d31999cb23565c0725c61df74a2660 | 2026-06-01T20:11:58Z | old 84-row export; deploy copy is the served one |
| databases/berkeley_energy_use.db | archive/orphans/berkeley_energy_use.db | 35b5901879bda8af44a54f976264ebadb4d09ef073e98f0fa2cdda14370c0325 | 2026-06-01T20:11:58Z | BESO standalone, no script ref |
| databases/berkeley_housing_apr.db | archive/orphans/berkeley_housing_apr.db | c2bd4366ff9bb1e0a8216088a303eb39e9592f38b222928338f08d068066eabe | 2026-06-01T20:11:58Z | frozen APR snapshot, no script ref |
| berkeleyshops-audience/audience.db | archive/orphans/audience.db | 25000b6c942104b7c674bc0a7055a058971d202e0fb689bb5f394453295f203f | 2026-06-01T20:11:58Z | separate shops-mailing project |
| berkeleyshops-audience/archive/audience_2026-03-12.db | archive/orphans/audience_2026-03-12.db | 3f9e62a88a7aebf26e4e1959320bfe9dddbcfb55c673b8e9fb71e55277a34743 | 2026-06-01T20:11:58Z | older audience copy |
| business_licenses.db | archive/orphans/business_licenses.db | 5aeec9467850d244d3a2adfa58531082795d9aacde7ac84a09029cefcccbd7a7 | 2026-06-01T20:11:58Z | 12882 licenses subset of berkeley.db.licenses(13004) |
| databases/berkeley_data.db | archive/orphans/berkeley_data.db | 27baf30f0a05f96cefe222e5b9705d9781b1226138755b4f4c5a8ef270a33374 | 2026-06-01T20:11:58Z | 13004 business_licenses = berkeley.db.licenses; preserved there |
| data/processed/pipeline.db | archive/orphans/pipeline.db | 61e8e0765d758d7d5a63b696804c2c00cd827d229cc48a147a635824b7b62d56 | 2026-06-01T20:11:58Z | V1 163-proj orphan, no production ref |
