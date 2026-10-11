# 踩坑实录（4 轮实战沉淀，照做可省数小时）

## 1. 内联 heredoc 传 Windows 路径会被 MSYS 改写
**现象**：在 Bash 工具里用 `python - <<'PY' ... PY` 跑脚本，路径 `D:\KnowsB` 被
静默转成 `D:/KnowsB`，导致 `sqlite3` 查询匹配不到任何 root（一度误判"DB 空了"）。
**修复**：**所有跑 Python 的脚本都写成文件**，用 `python tools/_work/xxx.py` 调用；
文件里用 raw-string 或正斜杠 `os.path.abspath` 会自动归一。不要依赖内联 heredoc 传盘符路径。

## 2. 跨库判重前必须先把 KB 全文 SHA256 算满
**现象**：classify 时大量 A 类漏判（75/78 靠缺口闭环才补回），exec 阶段 G3 误报
"KB 副本大小不匹配"。根因：KB 索引里有 `sha256 IS NULL` 的文件（仅 18,649/29,172 算过）。
**修复**：分类前强制
`python hash_index.py full --root D:\KnowsB --full-all --db <db>`
classify 脚本也会打印 `kb_null_sha_files` 警告，看到 >0 就先回去补。

## 3. G2 新鲜度门禁要以「分类 CSV 的 sha」为权威，而非易失扫描缓存
**现象**：exec 重算 sha 与扫描缓存 `c[2]` 比对，误报 3 个"内容变更"而中止。
**真相**：那 3 个是 `obj\Debug\TemporaryGeneratedFile_*.cs`（0 字节 MSBuild 生成物），
扫描瞬间被后台进程临时删/建，缓存缺失；但其**当前内容 == 分类时决定的 sha**。
**修复**：执行依据应是"分类 CSV 记录的 sha（我们决定要动那份内容）"，不是扫描缓存。
当前内容 == 分类 sha 即安全，可移动。

## 4. 零字节文件 sha 规整
**现象**：KB 把 0 字节文件存成 `""`，而源用规范空哈希 `EMPTY_SHA`；
`kb_rel_by_sha.get(EMPTY_SHA)` 返回 `""`，G3 找不到副本。
**修复**：载入 root 时统一规整——`size==0 → sha=EMPTY_SHA`
（`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`）。
classify / exec 两端都要做同样的规整。

## 5. 目标路径设计四大坑（manifest 阶段）
- **5a 只取二级目录 → 同名文件塌缩成重复目标**：应**镜像源相对路径的全部层级**。
- **5b 顶级单文件 rel 仅一段 → 退化成无文件名的文件夹**：单段时用 `[子目录名, 文件名]`。
- **5c 源内"文件夹与文件同名"**（如 `Workspace.sws/Workspace.sws`）→ 目标冲突：
  builder 内对目标路径加 `(2)`/`(3)`… 序号去重。
- **5d 循环变量名 `d` 覆盖了文件字典 `d`**：把所有"目录变量"改名（如 `tdir`），
  绝不用 `d` 当目录变量名。

## 6. 执行前必须预检（fail-closed）
源缺失 / 目标已存在冲突 / 重复目标 —— 任一不满足就**整体中止，一个文件都不动**。
`kb_ingest.py` 已实现：预检不过 `raise SystemExit(2)`。

## 7. 同盘改名 = 真移动；HOLD 隔离可逆；最终删除归用户
- 同盘（都在 D:）`os.replace` 是改名，源立刻消失、空间不翻倍（区别于复制）。
- 隔离到 `D:\_recycle_hold\<名>_<日期>\` 仍是可逆操作。
- 沙箱 `rm`/回收站 API 通常不可用 → **永久删除一律交给用户手动做**，脚本只负责隔离。

## 8. BpgYx 型大目录：先弄清"文档去哪了"再动残骸
**现象**：`D:\BpgYx` 原 92,984 文件 / 60.91 GB，A1 隔离后剩 29,977 / 5.92 GB，
且只剩 67 个文档（≈0 GB）。剩余全是 `.tpb`(SiboView)2.08G、`.svn-base`1.56G、`.dll`1.02G、
`.pv`/`.dbf`/源码等——**非知识文档**。
**关键风险**：原本约 1.7 万知识文档既不在 BpgYx 也不在 KnowsB（KnowsB 只 +526）。
**修复**：在确认文档已进 ima / 别处之前，**不要删 BpgYx 残骸**。先追查去向。
