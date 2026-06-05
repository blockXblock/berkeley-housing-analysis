"""
Two gated fixes (2026-06-04). DRY by default; --commit to write. Base: dea44e46.
FIX 1: ingest Logan Park SOUTH Building (APN 055189504100, B2021-03302, 69u, Finaled
       2023-08-08) — a genuine 2023 completion we were missing. CY2023 631 -> 700.
FIX 2: correct 1367 University (proj158): stage Withdrawn->Completed; drop stray
       2025-06-18 co event (no permit); keep permit-backed 2025-05-06. No count change.
"""
import sqlite3, sys
DB='databases/berkeley_housing_v2.db'
PROV="CPRA BP Annual Permit Report (B2021-03302, Finaled 2023-08-08, status Finaled) primary-permit-confirmed; Logan Park South Building 2026-06-04"
DRY=('--commit' not in sys.argv)
v=sqlite3.connect(DB); v.row_factory=sqlite3.Row; cur=v.cursor()
cur.execute("PRAGMA foreign_keys=OFF"); cur.execute("BEGIN")
try:
    pre={y:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for y in ('2018','2019','2020','2021','2022','2023','2024','2025','2026')}
    n0=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    # ===== FIX 1 — Logan Park South Building (new project) =====
    cur.execute("INSERT INTO parcels (city_id,apn,address,geometry_source,notes) VALUES (1,?,?,?,?)",('055 189504100','2352 Shattuck Ave','alameda_assessor',PROV+' [parcel not in assessor -> coords NULL]')); pc=cur.lastrowid
    cur.execute("INSERT INTO projects (city_id,canonical_name,canonical_address,normalized_address,latitude,longitude,current_stage_type_id) VALUES (1,?,?,?,?,?,6)",
                ('Logan Park South Building','2352 Shattuck Ave (South Building)','2352|SHATTUCK',None,None)); pid=cur.lastrowid
    cur.execute("INSERT INTO documents (project_id,title,permit_number,source_system,notes) VALUES (?,?,?,?,?)",(pid,'CPRA BP Annual Permit Report 2018-2022',' B2021-03302','cpra',PROV)); doc=cur.lastrowid
    cur.execute("INSERT INTO project_versions (project_id,version_label,version_type_id,effective_date,total_units,is_current,source_document_id,asserted_by,confidence_type_id,description) VALUES (?,?,5,?,?,1,?,?,2,?)",
                (pid,'as-built (CPRA Finaled)','2023-08-08',69,doc,PROV,'Phase II of South Building: Architectural, Structural Super Structure, MEP and landscaping (69u permit-stated NumberUnits)')); vid=cur.lastrowid
    cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
    cur.execute("INSERT INTO unit_program (project_version_id,bedroom_count,tenure_type_id,unit_count,source_document_id,asserted_by,confidence_type_id,notes) VALUES (?,NULL,8,?,?,?,2,?)",(vid,69,doc,PROV,'69u permit-stated (B2021-03302 NumberUnits); bedroom/tenure Unknown')); up=cur.lastrowid
    cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (?,6,?,?,?,2)",(up,69,doc,PROV))
    cur.execute("INSERT INTO project_parcels (project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,pc))
    cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra','B2021-03302',None,'2023-08-08',None,'Phase II of South Building: Structural Super Structure, MEP, landscaping')); perm=cur.lastrowid
    cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'city_portal',?)",(pid,'2023-08-08',perm,'CO from CPRA Finaled 2023-08-08 (B2021-03302, Finaled status). Logan Park South Building — separate structure from North (proj179, 2022).'))
    cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,26,'2026-06-04',?,1,2,'inferred',?)",(pid,perm,'Permit classified PRIMARY (major structural completion, primary-permit-confirmed)'))
    southpid=pid

    # ===== FIX 2 — correct 1367 University (proj158) =====
    cur.execute("UPDATE projects SET current_stage_type_id=6 WHERE id=158 AND current_stage_type_id=8"); assert cur.rowcount==1, "proj158 stage not withdrawn?"
    cur.execute("DELETE FROM project_events WHERE id=289 AND project_id=158 AND event_type_id=17 AND permit_id IS NULL"); assert cur.rowcount==1, "stray 2025-06-18 co event 289 not found"

    # ===== VERIFICATION =====
    post={y:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for y in pre}
    south=cur.execute("SELECT co_issued_date co, total_units u, status_label sl FROM v_projects_flat WHERE project_id=?",(southpid,)).fetchone()
    u158=cur.execute("SELECT co_issued_date co, total_units u, status_label sl FROM v_projects_flat WHERE project_id=158").fetchone()
    fk=cur.execute("PRAGMA foreign_key_check").fetchall(); integ=cur.execute("PRAGMA integrity_check").fetchone()[0]
    nproj=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print("=== VERIFICATION ===")
    print("  per-year: " + " ".join(f"CY{y}:{pre[y]}->{post[y]}" for y in pre))
    print(f"  South Building (proj{southpid}): co={south['co']} units={south['u']} stage={south['sl']}  (expect 2023-08-08/69/Completed)")
    print(f"  1367 University (proj158): co={u158['co']} units={u158['u']} stage={u158['sl']}  (expect 2025-05-06/39/Completed)")
    print(f"  projects {n0}->{nproj} (+{nproj-n0}) | FK={len(fk)} | integrity={integ}")
    exp={'2018':70,'2019':98,'2020':76,'2021':107,'2022':84,'2023':700,'2024':709,'2025':531,'2026':216}
    ok=(all(post[y]==exp[y] for y in exp) and south['co']=='2023-08-08' and south['u']==69
        and u158['co']=='2025-05-06' and u158['sl']=='Completed' and len(fk)==0 and integ=='ok')
    if ok and not DRY:
        cur.execute("PRAGMA foreign_keys=ON"); v.commit(); print("\nALL CHECKS PASS -> COMMITTED")
    elif ok:
        v.rollback(); print("\nALL CHECKS PASS -> DRY RUN rolled back")
    else:
        v.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK ***  (expected: " + " ".join(f"CY{y}={exp[y]}" for y in exp) + ")")
except Exception as e:
    v.rollback(); print("EXCEPTION -> ROLLED BACK:", repr(e))
