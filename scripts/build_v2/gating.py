"""Shared gating/snapshot helper for the v2-from-sources rebuild — used by EVERY stage's write.

A snapshot is a ROLLBACK POINT; it must never be clobbered. So `snapshot_v3` REFUSES to overwrite an
existing snapshot — a second write (e.g. an idempotency re-run) finds it and leaves the original
pre-write state intact, returning (path, created=False).

LESSON (why this exists): S1's idempotency RE-RUN clobbered its own pre-write snapshot, because the
write used a FIXED tag and the verification re-ran `--write`, overwriting `pre-s1-rerun.db` with the
already-written state. Verification must be NON-MUTATING with respect to the state it protects. Fixed
here once, for S1/S2/S3 and every future stage.
"""
import os, shutil

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
AS_OF = '2026-06-17'


def snapshot_v3(tag, v3_path=V3, as_of=AS_OF):
    """Create keep_snapshot_<as_of>_pre-<tag>.db as a rollback point BEFORE a gated write.
    REFUSES to overwrite an existing snapshot (returns it with created=False) so a re-run /
    idempotency verification can never clobber the rollback state the real write created.
    Returns (snapshot_path, created: bool)."""
    snap = os.path.join(os.path.dirname(v3_path), f'keep_snapshot_{as_of}_pre-{tag}.db')
    if os.path.exists(snap):
        return snap, False                 # rollback point already exists -> DO NOT clobber
    shutil.copy(v3_path, snap)
    return snap, True
