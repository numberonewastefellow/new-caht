#!/usr/bin/env bash
# Needs scratch inputs in D:/tmp/p1: baseline_old.sql (git show <pre-fold rev>:backend/alembic/versions/0001_baseline_schema.sql),
# schema_routeB_A1.sql + data_routeB_A1.sql (pg_dump -s / -a --column-inserts of a DB built from the OLD baseline).
# Needs the live api container image om/om-backend:latest and the live Postgres container for route F.
# Migration matrix on throwaway Postgres containers. Mounts the working-tree alembic dir over the image.
export MSYS_NO_PATHCONV=1
B=D:/llm/danswer20022026/backend; N=om-mx-net; cd /d/tmp/p1
docker network create $N >/dev/null 2>&1
mk(){ docker rm -f $1 >/dev/null 2>&1; docker run -d --name $1 --network $N -e POSTGRES_PASSWORD=password postgres:15.2-alpine >/dev/null; for i in $(seq 1 30); do docker exec $1 pg_isready -U postgres >/dev/null 2>&1 && break; sleep 2; done; sleep 3; }
alem(){ docker run --rm --network $N -v $B/alembic:/app/alembic:ro -e POSTGRES_HOST=$1 -e POSTGRES_PASSWORD=password om/om-backend:latest sh -c "$2"; }
dump(){ docker exec $1 pg_dump -U postgres -s --no-owner --no-acl postgres > $2 2>/dev/null; }
echo "[A] fresh empty DB -> head (new baseline)"; mk mx-A
alem mx-A 'echo upgrades=$(alembic upgrade head 2>&1 | grep -c "Running upgrade"); echo errors_on_rerun=$(alembic upgrade head 2>&1 | grep -cE "Error|Traceback")'; dump mx-A mx_A.sql
docker exec mx-A pg_dump -U postgres -a --column-inserts --no-owner --no-acl postgres > mx_A_data.sql 2>/dev/null
echo "[D] legacy DB (old baseline via psql, stamped 0001) -> head"; mk mx-D; docker cp D:/tmp/p1/baseline_old.sql mx-D:/tmp/b.sql; docker exec mx-D sh -c 'psql -U postgres -q -v ON_ERROR_STOP=1 -f /tmp/b.sql >/dev/null 2>&1; echo load=$?'
alem mx-D 'alembic stamp 0001_baseline_schema >/dev/null 2>&1; echo upgrades=$(alembic upgrade head 2>&1 | grep -c "Running upgrade")'; dump mx-D mx_D.sql
echo "[E] mid-history (old baseline, 0001 -> 0003 genuinely run, then head)"; mk mx-E; docker cp D:/tmp/p1/baseline_old.sql mx-E:/tmp/b.sql; docker exec mx-E sh -c 'psql -U postgres -q -v ON_ERROR_STOP=1 -f /tmp/b.sql >/dev/null 2>&1'
alem mx-E 'alembic stamp 0001_baseline_schema >/dev/null 2>&1; alembic upgrade 0003_agent_rename >/dev/null 2>&1; echo upgrades_after_0003=$(alembic upgrade head 2>&1 | grep -c "Running upgrade")'; dump mx-E mx_E.sql
echo "[F] live dump copy -> head (must be a no-op)"; docker exec virtualai-relational_db-1 pg_dump -U postgres -Fc postgres > mx_live.dump; mk mx-F; docker exec -i mx-F pg_restore -U postgres -d postgres --no-owner < mx_live.dump >/dev/null 2>&1
b=$(docker exec mx-F psql -U postgres -Atc "select count(*) from chat_session"); alem mx-F 'echo upgrades=$(alembic upgrade head 2>&1 | grep -c "Running upgrade")'; echo "chat_session rows $b -> $(docker exec mx-F psql -U postgres -Atc 'select count(*) from chat_session')"
echo "[G] second schema via -x schemas=tenant_test"; mk mx-G
alem mx-G 'echo upgrades=$(alembic -x schemas=tenant_test -x create_schema=true upgrade head 2>&1 | grep -c "Running upgrade")'
docker exec mx-G psql -U postgres -Atc "select (select version_num from tenant_test.alembic_version)||' | '||(select string_agg(column_name,',') from information_schema.columns where table_schema='tenant_test' and table_name='chat_session' and column_name like '%bot_flow')||' | agents='||(select count(*) from tenant_test.agent)||' tools='||(select count(*) from tenant_test.tool)"
python - <<'PY'
import re,difflib
def norm(p):
    s=open(p,encoding="utf-8").read(); s=re.sub(r"^--.*$","",s,flags=re.M); s=re.sub(r"^SET .*$|^SELECT pg_catalog.*$","",s,flags=re.M)
    return [l.rstrip() for l in s.splitlines() if l.strip()]
ref=norm("schema_routeB_A1.sql")
for f,l in [("mx_A.sql","A fresh/new baseline"),("mx_D.sql","D legacy"),("mx_E.sql","E mid-history")]:
    d=[q for q in difflib.unified_diff(ref,norm(f),lineterm="",n=0) if not q.startswith(("---","+++","@@"))]
    print(f"schema {l:22} vs old-baseline reference: differing={len(d)}", d[:2])
d=[q for q in difflib.unified_diff(norm("data_routeB_A1.sql"),norm("mx_A_data.sql"),lineterm="",n=0) if not q.startswith(("---","+++","@@"))]
print("seed data A vs reference: differing =",len(d))
PY
docker rm -f mx-A mx-D mx-E mx-F mx-G >/dev/null 2>&1; docker network rm $N >/dev/null 2>&1; echo "scratch cleaned"
