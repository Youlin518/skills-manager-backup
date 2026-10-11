---
name: kb-archive-ingest
description: "This skill should be used when consolidating scattered enterprise document folders into a structured knowledge base (e.g. D:\\KnowsB), or de-duplicating a source directory against an existing knowledge base. It covers the full pipeline: read-only census, persistent multi-root SHA256 hashing, content-based A/B/C classification (A=already-in-KB redundant, B=internal duplicate, C=unique), producing a confirmation manifest, then reversible same-disk isolation/ingestion with fail-closed verification. Applicable to Windows/NTFS knowledge-base organization, large-archive cleanup, and KB build-out where documents and code are kept in separate libraries (KnowsB vs KnowsCode)."
agent_created: true
---

# 知识库归档去重入库 (kb-archive-ingest)

## Overview

把散落的 `D:\xx` 源目录，按内容去重后整合进结构化知识库 `D:\KnowsB`（文档）与
`D:\KnowsCode`（代码/工程二进制）。流程为六阶段：普查 → 哈希 → 分类 A/B/C →
出清单（用户确认）→ 同盘改名入库/隔离（可逆）→ 收尾。已实战跑通 4 轮
（BpgYx / EMSDocuments / 02产品 / 02研发产品管理）。

**核心约束（用户强规则，任何执行前必须守）**
1. 先出清单，用户确认后再动文件。
2. 保留原始文件、先做副本/同盘改名（可逆）；永久删除由用户手动做。
3. 沙箱 SAFE_DELETE 为 fail-closed：本工序只做"同盘改名隔离/入库"，不永久删。

## When to trigger

- 用户说"处理这个目录，和之前 BpgYx/02产品 流程一致""把 xx 入库 KnowsB""清理 xx 重复文件"。
- 任务是建立/扩充企业知识库、对大目录去重、把独有资料按业务域归档。
- 涉及 KnowsB / KnowsCode 两个库的目录架构与内容路由。

## Usage (step-by-step)

完整工序见 `references/workflow.md`（含 Phase 0–6、决策速查表）。关键步骤：

### 1) 普查（只读，不碰文件）
统计文件数/体积/扩展名/是否含 `.svn`/目录结构。脚本一律写成文件再用
`python xxx.py` 调用（**勿用内联 heredoc 传 Windows 路径**——见 pitfalls #1）。

### 2) 哈希：先补满 KB，再加入源
```bash
python scripts/hash_index.py full  --root D:\KnowsB --full-all --db <db>
python scripts/hash_index.py build --root D:\<源>   --full-all --db <db>
python scripts/hash_index.py stat  --db <db>
```
`<db>` 用 `D:\KnowsB\00-知识库索引\KnowsB-Hash-Index.sqlite3`（多根同库）。
**KB 必须全文 sha 算满**，否则 A 类漏判、exec 阶段 G3 误报（pitfalls #2）。

### 3) 分类 A/B/C
```bash
python scripts/kb_classify.py --source-root D:\<源> --source-name <名> \
    --kb-root D:\KnowsB --db <db> --out-dir <dir> \
    [--other-roots "D:\BpgYx;D:\SVN\EMSDocuments"]
```
输出 `<名>_A/B/C_*.csv` + `_classify_summary.json`。**自检必过**：
`A + B删 + B留 + C == 源总数`；A 类抽样逐字节核验应 100% 一致。

### 4) 出清单（manifest），交用户确认 —— 停在这
- C 类按业务域映射进 KnowsB（见 `references/knowsb_domains.md`），必要时标**新增域**。
- A/B 类目标 = 隔离 HOLD（保留相对路径层级）。
- 代码/工程二进制 → KnowsCode，不进 KnowsB。
- **目标路径规则**（否则执行塌缩/冲突，pitfalls #5）：
  镜像源全部层级；单段 rel 用 `[子目录,文件名]`；同名目录/文件加 `(2)(3)`；
  循环变量别用 `d`。
- 交两份：可读清单文档 + manifest CSV（列：源绝对路径, 目标绝对路径, 类别）。
- **等用户确认后再进入 Phase 5。**

### 5) 执行（同盘改名，fail-closed）
```bash
python scripts/kb_ingest.py --manifest <清单>.csv
```
预检（源缺失/目标冲突/重复目标）任一不过 → 整体中止，0 移动。成功逐文件三向对账，
产出 `move_log.csv`。

### 6) 收尾
- 告知用户：**手动删**对应 HOLD 才释放空间。
- 入库后**重扫 KB 哈希索引**（`hash_index.py build --root D:\KnowsB`）——推送 ima 前必做。

## Resources

- `scripts/hash_index.py` — 多根、分层、可中断续跑的 SHA256 索引器（build/scan/quick/full/stat/export/sha）。
- `scripts/kb_classify.py` — 通用 A/B/C 分类器（参数：源根/KB根/DB/输出目录/可选二次对比根）。
- `scripts/kb_ingest.py` — 清单驱动的入库/隔离执行器（预检 fail-closed + 逐文件三向对账 + 还原日志）。
- `references/workflow.md` — 六阶段标准工序 + 决策速查表。
- `references/pitfalls.md` — 8 条实战踩坑（含 MSYS 路径、KB 补 sha、G2 权威判据、空哈希规整、目标路径设计、fail-closed、BpgYx 残骸）。
- `references/knowsb_domains.md` — KnowsB/KnowsCode 业务域路由表与启发式。
