"""
CY2023 Pass 2 — corrections (4 verified projects). DRY by default; --commit to write.
These CORRECT existing v2 projects (not clean inserts). Snapshot:
keep_snapshot_2026-06-03_pre-cy2023-pass2.db (a5e63b1b).
2352 Logan Park (2022, pre-cycle) and 2210 MLK (unresolved) are NOT touched.
"""
import sqlite3, sys
DB='databases/berkeley_housing_v2.db'
PROV="Accela Building module (verified pull 2026-06-03); CY2023 Pass 2 corrections"
DRY=('--commit' not in sys.argv)
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row; cur=db.cursor()
cur.execute("PRAGMA foreign_keys=OFF"); cur.execute("BEGIN")
try:
    pre={y:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for y in ('2023','2024','2025','2026')}

    def add_permit(pid,bp,fin,val,desc):
        cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'accela',bp,None,fin,val,desc)); return cur.lastrowid
    def add_co(pid,date,perm,summary):
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'city_portal',?)",(pid,date,perm,summary))
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,26,'2026-06-03',?,1,2,'inferred',?)",(pid,perm,"Permit classified PRIMARY (Accela-verified 2023 structural Final, CY2023 Pass 2)"))

    # --- proj168 3000 San Pablo: 29 In Review -> 78 Completed, CO 2023-06-05 (permit-stated 78u) ---
    p=add_permit(168,'B2020-04316','2023-06-05',None,'78-unit residential (Accela Building, Finaled 2023-06-05)')
    cur.execute("UPDATE project_versions SET total_units=78 WHERE id=165")
    cur.execute("UPDATE unit_program SET unit_count=78 WHERE id=165")
    cur.execute("UPDATE unit_program_affordability SET unit_count=78 WHERE id=160")
    cur.execute("UPDATE projects SET current_stage_type_id=6 WHERE id=168")
    add_co(168,'2023-06-05',p,'CO from Accela Finaled 2023-06-05 (B2020-04316). Corrects prior 29u/In Review; 78u permit-stated.')

    # --- proj182 2072 Addison: Entitled -> Completed, CO 2023-07-18 (66u, matches CKAN) ---
    p=add_permit(182,'B2018-04293','2023-07-18',None,'66-unit residential (Accela Building, Finaled 2023-07-18)')
    cur.execute("UPDATE projects SET current_stage_type_id=6 WHERE id=182")
    add_co(182,'2023-07-18',p,'CO from Accela Finaled 2023-07-18 (B2018-04293). Corrects prior Entitled/no-CO; 66u permit-stated.')

    # --- proj91 2009 Addison: 0u/anomaly -> 45u Completed, CO 2023-04-04 (45u CKAN-DERIVED, not permit-stated) ---
    p=add_permit(91,'B2019-02956','2023-04-04',None,'Multi-unit residential (Accela Building, Finaled 2023-04-04); unit count CKAN-derived')
    cur.execute("UPDATE project_versions SET total_units=45 WHERE id=89")
    cur.execute("UPDATE unit_program SET unit_count=45 WHERE id=89")
    cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (89,6,45,NULL,?,2)",(PROV+' [unit count CKAN-derived, not permit-stated]',))
    add_co(91,'2023-04-04',p,'CO from Accela Finaled 2023-04-04 (B2019-02956). Corrects prior 0u/no-CO anomaly. 45u CKAN-derived (flag).')

    # --- proj304 605 Neilson: WRONG 2025-09-04 -> 2023-04-20 (moves CY2025 -> CY2023) ---
    cur.execute("DELETE FROM project_events WHERE id=3023 AND project_id=304 AND event_type_id=17")  # the wrong 2025 CO (B2022-06065)
    assert cur.rowcount==1, "605 Neilson wrong CO event 3023 not found"
    p=add_permit(304,'B2020-00481','2023-04-20',None,'1-unit ADU (Accela Building, Finaled 2023-04-20)')
    add_co(304,'2023-04-20',p,'CO re-dated to Accela Finaled 2023-04-20 (B2020-00481). Prior 2025-09-04 (B2022-06065) was a wrong-pick; real ADU completion is 2023.')

    # === VERIFICATION ===
    print("=== DRY-RUN VERIFICATION ===")
    post={y:cur.execute(f"SELECT COUNT(*) c, COALESCE(SUM(total_units),0) u FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN (165,170,171,177)").fetchone() for y in ('2023','2024','2025','2026')}
    chk={pid:cur.execute("SELECT co_issued_date co, total_units tu, status_label sl FROM v_projects_flat WHERE project_id=?",(pid,)).fetchone() for pid in (168,182,91,304,362,179)}
    fk=cur.execute("PRAGMA foreign_key_check").fetchall(); integ=cur.execute("PRAGMA integrity_check").fetchone()[0]
    for y in ('2023','2024','2025','2026'):
        flag='' if pre[y]==post[y]['u'] else f'  <-- CHANGED from {pre[y]}'
        print(f"  CY{y}: {post[y]['c']} proj / {post[y]['u']} units{flag}")
    print(f"\n  corrections applied:")
    print(f"    168 3000 SanPablo: co={chk[168]['co']} units={chk[168]['tu']} stage={chk[168]['sl']}  (expect 2023-06-05/78/Completed)")
    print(f"    182 2072 Addison:  co={chk[182]['co']} units={chk[182]['tu']} stage={chk[182]['sl']}  (expect 2023-07-18/66/Completed)")
    print(f"    91  2009 Addison:  co={chk[91]['co']} units={chk[91]['tu']}  (expect 2023-04-04/45)")
    print(f"    304 605 Neilson:   co={chk[304]['co']}  (expect 2023-04-20; was 2025-09-04)")
    print(f"  untouched (holds): 362 MLK co={chk[362]['co']} (stays CY2025) | 179 Logan Park co={chk[179]['co']} (stays uncounted, 2022 finding)")
    print(f"  FK rows={len(fk)} | integrity={integ}")
    ok=(post['2023']['u']==631 and post['2024']['u']==709 and post['2026']['u']==216 and len(fk)==0 and integ=='ok'
        and chk[168]['co']=='2023-06-05' and chk[182]['co']=='2023-07-18' and chk[91]['co']=='2023-04-04' and chk[304]['co']=='2023-04-20')
    if ok and not DRY:
        cur.execute("PRAGMA foreign_keys=ON"); db.commit(); print("\nALL CHECKS PASS -> COMMITTED")
    elif ok:
        db.rollback(); print("\nCORE CHECKS PASS -> DRY RUN rolled back (note CY2025 moved to 531 — see report)")
    else:
        db.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK ***")
except Exception as e:
    db.rollback(); print("EXCEPTION -> ROLLED BACK:", repr(e))
