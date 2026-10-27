"""Move existing file-store objects from the legacy upstream bucket/prefix to the om names.

Why this is safe to run on a live system
  * Reads always use the ``bucket_name`` and ``object_key`` stored on each ``file_record`` row, so files
    keep working before, during and after the move. New files already use the om defaults.
  * Default mode is a DRY RUN (nothing is copied or updated).
  * ``--apply`` copies each object server-side, verifies size and ETag at the destination, and only then
    updates the row; rows are updated in small transactions, so an interruption loses nothing and the
    script can simply be run again (already-moved rows are skipped).
  * Old objects are NEVER removed by ``--apply``. ``--delete-old`` is a separate, explicit pass that only
    deletes an old object after confirming the destination copy exists with the same size.

Usage (inside the api_server container, from /app):
  python scripts/migrate_file_store_names.py                 # dry run, prints what would move
  python scripts/migrate_file_store_names.py --apply         # copy + verify + update rows
  python scripts/migrate_file_store_names.py --delete-old    # after you verified the app, remove old copies
Options: --old-bucket --new-bucket --old-prefix --new-prefix --batch N --tenant TENANT_ID
"""

import argparse
import sys
from dataclasses import dataclass

from botocore.exceptions import ClientError
from sqlalchemy import select

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SqlEngine
from om.db.models import FileRecord
from om.file_store.file_store import get_s3_file_store
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR


@dataclass
class Move:
    file_id: str
    old_bucket: str
    old_key: str
    new_bucket: str
    new_key: str


def _map_location(
    bucket: str, key: str, ob: str, nb: str, op: str, np: str
) -> tuple[str, str] | None:
    """Return the new (bucket, key) for a legacy location, or None if it is not legacy."""
    new_bucket = nb if bucket == ob else bucket
    if key == op or key.startswith(op + "/"):
        new_key = np + key[len(op) :]
    else:
        new_key = key
    if (new_bucket, new_key) == (bucket, key):
        return None
    return new_bucket, new_key


def _ensure_bucket(s3, bucket: str) -> None:  # type: ignore[no-untyped-def]
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
        else:
            raise


def _head(s3, bucket: str, key: str) -> dict | None:  # type: ignore[no-untyped-def]
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old-bucket", default="onyx-file-store-bucket")
    ap.add_argument("--new-bucket", default="om-file-store-bucket")
    ap.add_argument("--old-prefix", default="onyx-files")
    ap.add_argument("--new-prefix", default="om-files")
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--tenant", default="public")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="copy objects and update file_record rows")
    mode.add_argument("--delete-old", action="store_true", help="remove old objects whose new copy is verified")
    args = ap.parse_args()

    SqlEngine.init_engine(pool_size=2, max_overflow=0)
    CURRENT_TENANT_ID_CONTEXTVAR.set(args.tenant)
    s3 = get_s3_file_store()._get_s3_client()

    with get_session_with_current_tenant() as db:
        rows = db.execute(select(FileRecord.file_id, FileRecord.bucket_name, FileRecord.object_key)).all()

    moves: list[Move] = []
    already = 0
    for file_id, bucket, key in rows:
        target = _map_location(bucket, key, args.old_bucket, args.new_bucket, args.old_prefix, args.new_prefix)
        if target is None:
            already += 1
        else:
            moves.append(Move(file_id, bucket, key, target[0], target[1]))
    print(f"file_record rows: {len(rows)} | already on new names: {already} | to move: {len(moves)}")

    if args.delete_old:
        return _delete_old(s3, rows, args)
    if not moves:
        return 0
    for m in moves[:3]:
        print(f"  e.g. {m.old_bucket}/{m.old_key}  ->  {m.new_bucket}/{m.new_key}")
    if not args.apply:
        print("DRY RUN: nothing changed. Re-run with --apply to move.")
        return 0

    _ensure_bucket(s3, args.new_bucket)
    done = failed = 0
    for i in range(0, len(moves), args.batch):
        verified: list[Move] = []
        for m in moves[i : i + args.batch]:
            src = _head(s3, m.old_bucket, m.old_key)
            if src is None:
                print(f"  SKIP {m.file_id}: source object missing at {m.old_bucket}/{m.old_key}")
                failed += 1
                continue
            dst = _head(s3, m.new_bucket, m.new_key)
            if dst is None:
                s3.copy_object(
                    CopySource={"Bucket": m.old_bucket, "Key": m.old_key},
                    Bucket=m.new_bucket,
                    Key=m.new_key,
                    MetadataDirective="COPY",
                )
                dst = _head(s3, m.new_bucket, m.new_key)
            if dst is None or dst["ContentLength"] != src["ContentLength"] or dst["ETag"] != src["ETag"]:
                print(f"  FAIL {m.file_id}: destination does not match source; row left unchanged")
                failed += 1
                continue
            verified.append(m)
        with get_session_with_current_tenant() as db:  # one short transaction per batch
            for m in verified:
                rec = db.get(FileRecord, m.file_id)
                if rec is not None:
                    rec.bucket_name, rec.object_key = m.new_bucket, m.new_key
            db.commit()
        done += len(verified)
        print(f"  batch {i // args.batch + 1}: moved {len(verified)} (total {done}/{len(moves)}, failed {failed})")
    print(f"DONE: moved {done}, failed {failed}. Old objects were kept; run --delete-old after verifying the app.")
    return 1 if failed else 0


def _delete_old(s3, rows, args) -> int:  # type: ignore[no-untyped-def]
    deleted = skipped = 0
    for _file_id, bucket, key in rows:
        if bucket != args.new_bucket:
            continue
        old_bucket = args.old_bucket
        old_key = args.old_prefix + key[len(args.new_prefix) :] if key.startswith(args.new_prefix + "/") else None
        if old_key is None:
            continue
        old, new = _head(s3, old_bucket, old_key), _head(s3, bucket, key)
        if old is None:
            continue
        if new is None or new["ContentLength"] != old["ContentLength"]:
            skipped += 1
            continue
        s3.delete_object(Bucket=old_bucket, Key=old_key)
        deleted += 1
    print(f"deleted {deleted} old objects, skipped {skipped} (no verified new copy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
