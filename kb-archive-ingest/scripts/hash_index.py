# -*- coding: utf-8 -*-
"""
可复用的文件哈希持久化索引工具（SQLite）—— 多根、分层、可中断续跑。

设计要点
--------
1. 持久化：哈希一次算好存库，之后不再重复计算。
2. 增量：以 (size, mtime_ns) 作为有效性判据；文件未变则直接复用缓存。
3. 可中断续跑：分批提交，任何时候被杀，下次接着算。
4. 分层计算，省 I/O：
     tier1 stat      —— 全部文件（极快）
     tier2 quick     —— 仅"存在同 size 同伴"的文件（头 64K + 尾 64K + size）
     tier3 sha256    —— 仅"quick 也相同"的文件（全文哈希）
   非重复文件永远不会被全文哈希。
5. 多根：一个库可容纳多个根目录（root 字段），知识库 / 各源目录都能进同一个库。

用法
----
  python hash_index.py build  --root D:\\KnowsB --db <db>
  python hash_index.py full   --root D:\\KnowsB --full-all --db <db>   # 强制全量全文 sha256
  python hash_index.py stat   --db <db>
  python hash_index.py export --db <db> --out x.csv
  python hash_index.py sha    --db <db> --path <file>
参数： --full-all  强制对所有文件算全文 sha256
"""
import os
import time
import sqlite3
import hashlib
import argparse

CHUNK = 1 << 20          # 1MB
QUICK_EDGE = 64 * 1024   # 头尾各 64KB
COMMIT_EVERY = 500

DEFAULT_DB = r"D:\KnowsB\00-知识库索引\KnowsB-Hash-Index.sqlite3"
DEFAULT_ROOT = r"D:\KnowsB"


def lp(p):
    """长路径前缀，避免 260 字符限制"""
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(p)
    return p


def open_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS files (
        root      TEXT NOT NULL,
        rel       TEXT NOT NULL,
        size      INTEGER,
        mtime_ns  INTEGER,
        quick     TEXT,
        sha256    TEXT,
        updated   TEXT,
        PRIMARY KEY (root, rel)
    );
    CREATE INDEX IF NOT EXISTS idx_size  ON files(size);
    CREATE INDEX IF NOT EXISTS idx_quick ON files(quick);
    CREATE INDEX IF NOT EXISTS idx_sha   ON files(sha256);
    CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    con.commit()
    return con


def set_meta(con, k, v):
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (k, str(v)))


def quick_sign(path, size):
    h = hashlib.sha256()
    h.update(str(size).encode())
    with open(lp(path), "rb") as f:
        if size <= 2 * QUICK_EDGE:
            h.update(f.read())
        else:
            h.update(f.read(QUICK_EDGE))
            f.seek(-QUICK_EDGE, os.SEEK_END)
            h.update(f.read(QUICK_EDGE))
    return h.hexdigest()


def full_sha(path):
    h = hashlib.sha256()
    with open(lp(path), "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def human(n):
    return f"{n/1e9:.2f} GB" if n >= 1e9 else f"{n/1e6:.1f} MB"


def do_scan(con, root):
    root = os.path.abspath(root)
    print(f"[tier1] 扫描 {root} ...", flush=True)
    seen = set()
    n_new = n_upd = n_same = 0
    cur = con.cursor()
    cache = {r: (s, m) for r, s, m in
             cur.execute("SELECT rel,size,mtime_ns FROM files WHERE root=?", (root,))}
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    batch = 0
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.startswith("KnowsB-Hash-Index.sqlite3"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            seen.add(rel)
            try:
                st = os.stat(lp(full))
            except OSError:
                continue
            old = cache.get(rel)
            if old and old[0] == st.st_size and old[1] == st.st_mtime_ns:
                n_same += 1
                continue
            if old:
                cur.execute(
                    "UPDATE files SET size=?,mtime_ns=?,quick=NULL,sha256=NULL,updated=? "
                    "WHERE root=? AND rel=?",
                    (st.st_size, st.st_mtime_ns, now, root, rel))
                n_upd += 1
            else:
                cur.execute(
                    "INSERT INTO files(root,rel,size,mtime_ns,quick,sha256,updated) "
                    "VALUES(?,?,?,?,NULL,NULL,?)",
                    (root, rel, st.st_size, st.st_mtime_ns, now))
                n_new += 1
            batch += 1
            if batch % COMMIT_EVERY == 0:
                con.commit()
    con.commit()
    gone = [r for r in cache if r not in seen]
    for i in range(0, len(gone), 500):
        chunk = gone[i:i + 500]
        cur.executemany("DELETE FROM files WHERE root=? AND rel=?",
                        [(root, r) for r in chunk])
    con.commit()
    print(f"[tier1] 新增 {n_new} / 变更 {n_upd} / 未变 {n_same} / 移除 {len(gone)}", flush=True)
    return n_new + n_upd


def do_quick(con, root, all_files=False):
    root = os.path.abspath(root)
    cur = con.cursor()
    if all_files:
        rows = cur.execute(
            "SELECT rel,size FROM files WHERE root=? AND quick IS NULL AND size>0",
            (root,)).fetchall()
    else:
        rows = cur.execute("""
            SELECT f.rel, f.size FROM files f
            WHERE f.root=? AND f.quick IS NULL AND f.size>0
              AND f.size IN (SELECT size FROM files GROUP BY size HAVING COUNT(*)>1)
        """, (root,)).fetchall()
    total = len(rows)
    print(f"[tier2] 需算 quick 的文件：{total}", flush=True)
    done = 0
    t0 = time.time()
    for rel, size in rows:
        full = os.path.join(root, rel)
        try:
            q = quick_sign(full, size)
        except Exception:
            q = "ERR"
        cur.execute("UPDATE files SET quick=? WHERE root=? AND rel=?", (q, root, rel))
        done += 1
        if done % COMMIT_EVERY == 0:
            con.commit()
    con.commit()
    print(f"[tier2] 完成 {done}，耗时 {time.time()-t0:.0f}s", flush=True)


def do_full(con, root, all_files=False):
    root = os.path.abspath(root)
    cur = con.cursor()
    if all_files:
        rows = cur.execute(
            "SELECT rel,size FROM files WHERE root=? AND root IS NOT NULL AND sha256 IS NULL AND size>0",
            (root,)).fetchall()
    else:
        rows = cur.execute("""
            SELECT f.rel, f.size FROM files f
            WHERE f.root=? AND f.sha256 IS NULL AND f.quick IS NOT NULL AND f.quick<>'ERR'
              AND f.quick IN (SELECT quick FROM files
                              WHERE quick IS NOT NULL GROUP BY quick HAVING COUNT(*)>1)
        """, (root,)).fetchall()
    total = len(rows)
    tbytes = sum(r[1] for r in rows)
    print(f"[tier3] 需算全文 sha256：{total} 个 / {human(tbytes)}", flush=True)
    done = 0
    dbytes = 0
    t0 = time.time()
    for rel, size in rows:
        full = os.path.join(root, rel)
        try:
            s = full_sha(full)
        except Exception:
            s = "ERR"
        cur.execute("UPDATE files SET sha256=? WHERE root=? AND rel=?", (s, root, rel))
        done += 1
        dbytes += size
        if done % 200 == 0:
            con.commit()
    con.commit()
    print(f"[tier3] 完成 {done}，耗时 {time.time()-t0:.0f}s", flush=True)


def do_stat(con):
    cur = con.cursor()
    print("=== 索引库状态 ===")
    for root, n, sz, nq, ns in cur.execute("""
        SELECT root, COUNT(*), SUM(size),
               SUM(CASE WHEN quick IS NOT NULL THEN 1 ELSE 0 END),
               SUM(CASE WHEN sha256 IS NOT NULL THEN 1 ELSE 0 END)
        FROM files GROUP BY root"""):
        print(f"  {root}\n    文件 {n}  体积 {human(sz or 0)}  quick已算 {nq}  sha256已算 {ns}")
    dup = cur.execute("""
        SELECT COUNT(*) FROM (SELECT sha256 FROM files WHERE sha256 IS NOT NULL
                              AND sha256<>'ERR' GROUP BY sha256 HAVING COUNT(*)>1)""").fetchone()[0]
    print(f"  已识别重复内容组：{dup}")


def do_export(con, out):
    import csv
    cur = con.cursor()
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["root", "rel", "size", "mtime_ns", "quick", "sha256", "updated"])
        for r in cur.execute("SELECT root,rel,size,mtime_ns,quick,sha256,updated FROM files"):
            w.writerow(r)
    print(f"已导出 -> {out}")


def do_sha_one(con, path):
    path = os.path.abspath(path)
    cur = con.cursor()
    for root, in cur.execute("SELECT DISTINCT root FROM files"):
        if path.lower().startswith(root.lower() + os.sep):
            rel = os.path.relpath(path, root)
            row = cur.execute("SELECT size,mtime_ns,sha256 FROM files WHERE root=? AND rel=?",
                              (root, rel)).fetchone()
            st = os.stat(lp(path))
            if row and row[0] == st.st_size and row[1] == st.st_mtime_ns and row[2]:
                print(row[2], "(cache)")
                return row[2]
            s = full_sha(path)
            cur.execute("INSERT OR REPLACE INTO files(root,rel,size,mtime_ns,quick,sha256,updated)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (root, rel, st.st_size, st.st_mtime_ns,
                         quick_sign(path, st.st_size), s,
                         time.strftime("%Y-%m-%d %H:%M:%S")))
            con.commit()
            print(s, "(computed)")
            return s
    s = full_sha(path)
    print(s, "(no-root, not cached)")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "scan", "quick", "full", "stat", "export", "sha"])
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--out", default="")
    ap.add_argument("--path", default="")
    ap.add_argument("--full-all", action="store_true")
    a = ap.parse_args()

    con = open_db(a.db)
    t0 = time.time()
    if a.cmd == "build":
        do_scan(con, a.root)
        do_quick(con, a.root, a.full_all)
        do_full(con, a.root, a.full_all)
        set_meta(con, "last_build_" + os.path.abspath(a.root),
                 time.strftime("%Y-%m-%d %H:%M:%S"))
        con.commit()
        do_stat(con)
    elif a.cmd == "scan":
        do_scan(con, a.root)
    elif a.cmd == "quick":
        do_quick(con, a.root, a.full_all)
    elif a.cmd == "full":
        do_full(con, a.root, a.full_all)
    elif a.cmd == "stat":
        do_stat(con)
    elif a.cmd == "export":
        do_export(con, a.out or "hash_index_export.csv")
    elif a.cmd == "sha":
        do_sha_one(con, a.path)
    print(f"[总耗时] {time.time()-t0:.0f}s")
    con.close()


if __name__ == "__main__":
    main()
