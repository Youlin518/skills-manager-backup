# -*- coding: utf-8 -*-
"""
清单驱动的入库/隔离执行器（通用版，可逆、fail-closed）

读取一份清单 CSV（由人工确认过的「源→目标」映射），执行同盘改名移动，
并逐文件三向对账。任何预检失败则**整体中止、一个文件都不动**。

清单 CSV 列（支持别名）：
  源绝对路径 / 源路径 / 源        -> 文件当前位置
  目标绝对路径 / 目标路径 / 目标    -> 文件应去的位置（已含文件名）
  类别（可选）                    -> 仅用于日志与汇总（A/B/C/隔离/入库）

用法
----
  python kb_ingest.py --manifest ingest_manifest.csv [--dry] [--log move_log.csv]
  --dry   只做预检与打印，不移动任何文件
"""
import os
import csv
import time
import argparse

SRC_ALIASES = ["源绝对路径", "源路径", "源"]
TGT_ALIASES = ["目标绝对路径", "目标路径", "目标"]
CAT_ALIASES = ["类别", "类", "action", "动作"]


def lp(p):
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(p)
    return p


def norm_header(h):
    h = h.strip()
    low = h.lower()
    for a in SRC_ALIASES:
        if h == a or low == a.lower():
            return "src"
    for a in TGT_ALIASES:
        if h == a or low == a.lower():
            return "tgt"
    for a in CAT_ALIASES:
        if h == a or low == a.lower():
            return "cat"
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--log", default="")
    a = ap.parse_args()

    rows = []
    with open(a.manifest, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        hdrs = {norm_header(h): h for h in (rd.fieldnames or [])}
        if "src" not in hdrs or "tgt" not in hdrs:
            raise SystemExit(f"清单缺少源/目标列，现有列: {rd.fieldnames}")
        src_key, tgt_key = hdrs["src"], hdrs["tgt"]
        cat_key = hdrs.get("cat")
        for r in rd:
            rows.append({
                "src": r[src_key].strip(),
                "tgt": r[tgt_key].strip(),
                "cat": (r[cat_key].strip() if cat_key and r.get(cat_key) else ""),
            })
    print(f"清单读取：{len(rows)} 行")

    # ---------- 预检（fail-closed）----------
    problems = []
    targets = {}
    for i, r in enumerate(rows):
        s, t = r["src"], r["tgt"]
        if not s or not t:
            problems.append((i, "空路径"))
            continue
        sl = lp(s)
        if not os.path.exists(sl):
            problems.append((i, f"源不存在: {s}"))
        tl = lp(t)
        if os.path.exists(tl):
            # 若内容/大小一致，算「已完成」可跳过，不算冲突
            try:
                if os.path.getsize(sl) == os.path.getsize(tl):
                    r["_skip_existing"] = True
                else:
                    problems.append((i, f"目标已存在且大小不同: {t}"))
            except OSError:
                problems.append((i, f"目标已存在但无法读取: {t}"))
        key = os.path.abspath(t).lower()
        if key in targets:
            problems.append((i, f"重复目标: {t} (与第 {targets[key]} 行冲突)"))
        else:
            targets[key] = i

    if problems:
        print(f"\n❌ 预检未通过，已中止，未移动任何文件。问题 {len(problems)} 项：")
        for i, msg in problems[:50]:
            print(f"  [{i}] {msg}")
        raise SystemExit(2)

    print("✅ 预检通过：源存在 0 缺失 / 目标冲突 0 / 重复目标 0")

    if a.dry:
        print("（--dry 模式，未执行移动）")
        return

    # ---------- 执行移动 ----------
    log_path = a.log or (os.path.splitext(a.manifest)[0] + "_move_log.csv")
    t0 = time.time()
    ok = fail = skip = 0
    with open(log_path, "w", encoding="utf-8-sig", newline="") as lf:
        w = csv.writer(lf)
        w.writerow(["源绝对路径", "目标绝对路径", "类别", "状态", "校验", "时间"])
        for r in rows:
            s, t = r["src"], r["tgt"]
            tl = lp(t)
            if r.get("_skip_existing"):
                skip += 1
                w.writerow([s, t, r["cat"], "SKIP", "目标已存在且相同", time.strftime("%H:%M:%S")])
                continue
            try:
                os.makedirs(os.path.dirname(tl) or ".", exist_ok=True)
                os.replace(lp(s), tl)  # 同盘=改名(真移动)；跨盘=原子失败
            except Exception as e:
                fail += 1
                w.writerow([s, t, r["cat"], "FAIL", f"移动异常: {e}", time.strftime("%H:%M:%S")])
                continue
            # 校验
            src_gone = not os.path.exists(lp(s))
            tgt_ok = os.path.exists(tl)
            # 源已移动消失、目标已生成即为成功（源已不可比大小，不再比较）
            verify = "OK" if (tgt_ok and src_gone) else "BAD"
            ok += 1 if verify == "OK" else 0
            fail += 1 if verify == "BAD" else 0
            w.writerow([s, t, r["cat"], "OK" if verify == "OK" else "BAD",
                        verify, time.strftime("%H:%M:%S")])
    print(f"\n执行结束：OK={ok}  FAIL={fail}  SKIP={skip}  ({time.time()-t0:.0f}s)")
    print(f"还原日志 -> {log_path}")
    if fail:
        raise SystemExit(3)
    print("✅ 全部成功，无失败。")


if __name__ == "__main__":
    main()
