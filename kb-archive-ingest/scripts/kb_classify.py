# -*- coding: utf-8 -*-
"""
知识库去重分类器（通用版）

把某个「源目录」按内容哈希与「知识库(KB)」对照，分出三类：
  A 类 = 内容已在 KB（冗余，可隔离到 HOLD 移除）
  B 类 = 源目录内部自重复（保留 1 份，其余删余）
  C 类 = 全局独有（应入库 KB，不可删）

可选 --other-roots：把 C 类再与这些根做二次对比，标注 also_in（仅供信息，
不改变 C 的结论——C 的定义是「对 KB 唯一」）。

硬前置（务必先执行）：
  python hash_index.py full --root <KB> --full-all   # 先把 KB 全文 sha 算全
否则 KB 大量 sha 为 NULL，A 类会漏判、exec 阶段 G3 会误报。

用法
----
  python kb_classify.py --source-root D:\\02产品 --source-name 02产品 \
      --kb-root D:\\KnowsB --db <db> --out-dir <dir> \
      [--other-roots "D:\\BpgYx;D:\\SVN\\EMSDocuments"]
"""
import os
import sys
import csv
import json
import time
import sqlite3
import hashlib
import argparse

CHUNK = 1 << 20
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def lp(p):
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(p)
    return p


def full_sha(path):
    h = hashlib.sha256()
    with open(lp(path), "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def norm_sha(size, raw):
    """零字节文件统一规整为 EMPTY_SHA；否则用原始 sha（None 时重算）。"""
    if size == 0:
        return EMPTY_SHA
    if raw and raw != "ERR":
        return raw
    return None  # 需要补算


def load_root(con, root):
    """返回 {(rel, size, sha)} 列表；sha 已规整（零字节→EMPTY_SHA）。"""
    rows = con.execute(
        "SELECT rel,size,sha256 FROM files WHERE root=?", (root,)).fetchall()
    out = []
    for rel, size, sha in rows:
        out.append((rel, size, norm_sha(size, sha)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--source-name", required=True)
    ap.add_argument("--kb-root", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--other-roots", default="")
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    SRC = os.path.abspath(a.source_root)
    KB = os.path.abspath(a.kb_root)
    con = sqlite3.connect(a.db, timeout=60)

    # ---- 0) 前置检查：KB 是否还有 NULL sha ----
    kb_null = con.execute(
        "SELECT COUNT(*) FROM files WHERE root=? AND sha256 IS NULL AND size>0",
        (KB,)).fetchone()[0]
    if kb_null:
        print(f"⚠️ KB 仍有 {kb_null} 个文件 sha 为 NULL；A 类可能漏判。"
              f"请先执行：python hash_index.py full --root {KB} --full-all")
    else:
        print("✅ KB 全文 sha 已齐，可安全分类")

    # ---- 1) 载入 KB ----
    kb_files = load_root(con, KB)
    kb_sha = {}          # sha -> [rel, ...]  （用于 A 类判定）
    kb_size_sha = {}     # size -> [ (rel, sha) ]  （用于缺口闭环）
    for rel, size, sha in kb_files:
        if sha is None:
            continue
        kb_sha.setdefault(sha, []).append(rel)
        kb_size_sha.setdefault(size, []).append((rel, sha))
    # KB 零字节文件集合（EMPTY_SHA 已在 kb_sha）
    kb_zero = len([1 for _, s, h in kb_files if s == 0])
    print(f"KB 文件数 {len(kb_files)}，含 sha 的 {sum(1 for *_,h in kb_files if h)}，"
          f"零字节 {kb_zero}")

    # ---- 1b) 二次对比根 ----
    other_sha = {}       # sha -> "root1,root2"
    for oroot in [r.strip() for r in a.other_roots.split(";") if r.strip()]:
        oroot = os.path.abspath(oroot)
        for _, _, h in load_root(con, oroot):
            if h:
                other_sha[h] = (other_sha.get(h, "") + "," + oroot).strip(",")

    # ---- 2) 载入源 ----
    src_files = load_root(con, SRC)
    # 补算源里 sha 仍为 None 的文件
    need = [(rel, size) for rel, size, sha in src_files if sha is None]
    if need:
        print(f"源有 {len(need)} 个文件 sha 缺失，现算…")
        cache = {(rel, size): sha for rel, size, sha in src_files}
        miss = 0
        for rel, size in need:
            try:
                h = full_sha(os.path.join(SRC, rel)) if size > 0 else EMPTY_SHA
            except Exception:
                h = "ERR"; miss += 1
            cache[(rel, size)] = h
        src_files = [(rel, size, cache[(rel, size)]) for rel, size, _ in src_files]
        print(f"  补算完成（失败 {miss}）")

    # ---- 3) 分组 + 分类 ----
    groups = {}          # sha -> [ (rel, size) ]
    for rel, size, sha in src_files:
        groups.setdefault(sha, []).append((rel, size))

    A, B_del, B_keep, C = [], [], [], []
    # 缺口闭环缓存：已补算的 KB (size,rel)
    kb_recompute_cache = {}

    def kb_counterpart_for_sha(sha, size, rel):
        """找到 KB 里内容相同的副本（含缺口闭环重算）。返回 rel 或 ''。"""
        if sha in kb_sha and kb_sha[sha]:
            # 取路径最浅（段数最少）的副本作为代表
            return min(kb_sha[sha], key=lambda r: (r.count(os.sep), len(r)))
        # 缺口闭环：KB 同 size 且 sha 为 NULL 的文件，现算对比
        for krel, ksha in kb_size_sha.get(size, []):
            if ksha is not None:
                continue
            if (size, krel) in kb_recompute_cache:
                if kb_recompute_cache[(size, krel)] == sha:
                    return krel
                continue
            try:
                kh = full_sha(os.path.join(KB, krel)) if size > 0 else EMPTY_SHA
            except Exception:
                kh = "ERR"
            kb_recompute_cache[(size, krel)] = kh
            if kh == sha:
                kb_sha.setdefault(sha, []).append(krel)
                return krel
        return ""

    g3_extra = 0
    for sha, members in groups.items():
        if sha in kb_sha and kb_sha[sha]:
            opp = min(kb_sha[sha], key=lambda r: (r.count(os.sep), len(r)))
            for rel, size in members:
                A.append({"rel": rel, "size": size, "sha256": sha, "kb_rel": opp})
        elif sha == EMPTY_SHA and kb_zero > 0:
            # 零字节文件：KB 也有零字节文件 → 视为 A
            opp = "(KB 零字节文件)"
            for rel, size in members:
                A.append({"rel": rel, "size": size, "sha256": sha, "kb_rel": opp})
        elif len(members) > 1:
            # B 类：保留路径最浅，其余删余
            keep = min(members, key=lambda m: (m[0].count(os.sep), len(m[0])))
            for rel, size in members:
                if (rel, size) == keep:
                    B_keep.append({"rel": rel, "size": size, "sha256": sha, "keep": 1})
                else:
                    B_del.append({"rel": rel, "size": size, "sha256": sha,
                                  "keep_rel": keep[0]})
        else:
            rel, size = members[0]
            # 缺口闭环：即便 sha 不在 kb_sha，也可能 KB 同 size 的 NULL 文件就是它
            opp = kb_counterpart_for_sha(sha, size, rel)
            if opp:
                g3_extra += 1
                A.append({"rel": rel, "size": size, "sha256": sha, "kb_rel": opp})
            else:
                also = other_sha.get(sha, "")
                C.append({"rel": rel, "size": size, "sha256": sha,
                          "ext": os.path.splitext(rel)[1].lower(),
                          "also_in": also})

    # ---- 4) 自检 ----
    total = len(src_files)
    chk = len(A) + len(B_del) + len(B_keep) + len(C)
    ok = (chk == total)
    print(f"自检：A={len(A)} B删={len(B_del)} B留={len(B_keep)} C={len(C)} "
          f"合计={chk} / 源总数={total} -> {'✅' if ok else '❌ 不守恒'}")

    # ---- 5) A 类抽样逐字节核验 ----
    sample = A[:80]
    bad = 0
    for r in sample:
        p = os.path.join(SRC, r["rel"])
        try:
            cur = full_sha(p) if r["size"] > 0 else EMPTY_SHA
        except Exception:
            cur = "ERR"
        if cur != r["sha256"]:
            bad += 1
    print(f"A 类逐字节核验（抽样 {len(sample)}）：一致 {len(sample)-bad} / 不一致 {bad}")
    # 缺口闭环一次性把 extra 记入 A 数（上面已 append）

    # ---- 6) 写 CSV / JSON ----
    base = os.path.join(a.out_dir, a.source_name)
    with open(base + "_A_dup_in_knowsb.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["源相对路径", "大小(字节)", "sha256", "KnowsB对应副本(相对)", "说明"])
        for r in A:
            w.writerow([r["rel"], r["size"], r["sha256"], r["kb_rel"], "内容已在KnowsB"])
    with open(base + "_B_self_dup.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["相对路径", "大小(字节)", "sha256", "动作", "保留副本"])
        for r in B_keep:
            w.writerow([r["rel"], r["size"], r["sha256"], "保留", r["rel"]])
        for r in B_del:
            w.writerow([r["rel"], r["size"], r["sha256"], "删除", r["keep_rel"]])
    with open(base + "_C_unique.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["相对路径", "大小(字节)", "sha256", "扩展名", "also_in(其它根)"])
        for r in C:
            w.writerow([r["rel"], r["size"], r["sha256"], r["ext"], r["also_in"]])

    summary = {
        "source": SRC,
        "source_name": a.source_name,
        "kb": KB,
        "total_source_files": total,
        "A_count": len(A), "A_bytes": sum(r["size"] for r in A),
        "B_del": len(B_del), "B_keep": len(B_keep), "B_bytes": sum(r["size"] for r in B_del),
        "C_count": len(C), "C_bytes": sum(r["size"] for r in C),
        "selfcheck_ok": ok,
        "gap_closure_caught": g3_extra,
        "kb_null_sha_files": kb_null,
        "A_byte_verify_sample": len(sample),
        "A_byte_verify_bad": bad,
    }
    with open(base + "_classify_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 分类完成，产物：")
    print(f"  {base}_A_dup_in_knowsb.csv  ({len(A)} 行)")
    print(f"  {base}_B_self_dup.csv       ({len(B_del)+len(B_keep)} 行)")
    print(f"  {base}_C_unique.csv         ({len(C)} 行)")
    print(f"  {base}_classify_summary.json")
    con.close()


if __name__ == "__main__":
    main()
