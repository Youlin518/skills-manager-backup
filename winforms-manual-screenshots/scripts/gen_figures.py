# -*- coding: utf-8 -*-
"""Generate 12 schematic interface mockups for MS.ExamSystemV1.1 manual.
Faithful to the WinForms source UI (colors, Chinese labels, layouts)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = "D:/tmp/figures"
os.makedirs(OUT, exist_ok=True)

REG = "C:/Windows/Fonts/msyh.ttc"
BOLD = "C:/Windows/Fonts/simhei.ttf"

_cache = {}
def f(size, bold=False):
    key = (size, bold)
    if key in _cache:
        return _cache[key]
    path = BOLD if bold else REG
    try:
        ft = ImageFont.truetype(path, size)
    except Exception:
        ft = ImageFont.truetype(REG, size)
    _cache[key] = ft
    return ft

# palette (from source)
DARK   = (49, 53, 59)      # 0x31,0x35,0x3B  title/nav bg
DARK2  = (38, 42, 48)      # active nav
BLUE   = (24, 144, 255)    # 0x18,0x90,0xFF
GREEN  = (76, 175, 80)     # 0x4C,0xAF,0x50
GTAG   = (82, 196, 26)     # example card type tag
RED    = (255, 77, 79)
ORANGE = (255, 152, 0)
PURPLE = (156, 39, 176)
LGBG   = (242, 244, 247)   # F2F4F7 light gray
BORDER = (220, 224, 230)
TXT    = (33, 33, 33)
GRAY   = (128, 128, 128)
LGRAY  = (225, 228, 233)
WHITE  = (255, 255, 255)
HDRBLUE = (31, 73, 125)    # table header fill

def txt(d, x, y, s, size, fill=TXT, bold=False, anchor="lm"):
    d.text((x, y), s, font=f(size, bold), fill=fill, anchor=anchor)

def rr(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def btn(d, x, y, w, h, label, bg=BLUE, fg=WHITE, size=13, radius=4, bold=False):
    rr(d, [x, y, x + w, y + h], radius, fill=bg)
    txt(d, x + w / 2, y + h / 2, label, size, fg, bold=bold, anchor="mm")

def field(d, x, y, w, h, text="", placeholder="", size=12):
    rr(d, [x, y, x + w, y + h], 4, fill=WHITE, outline=BORDER, width=1)
    if text:
        txt(d, x + 8, y + h / 2, text, size, TXT, anchor="lm")
    elif placeholder:
        txt(d, x + 8, y + h / 2, placeholder, size, GRAY, anchor="lm")

def grid(d, x, y, headers, rows, colw, rowh=28, fs=11, header_fill=HDRBLUE):
    total = sum(colw)
    cx = x
    for i, hname in enumerate(headers):
        d.rectangle([cx, y, cx + colw[i], y + rowh], fill=header_fill)
        txt(d, cx + colw[i] / 2, y + rowh / 2, hname, fs, WHITE, bold=True, anchor="mm")
        cx += colw[i]
    ry = y + rowh
    for ri, row in enumerate(rows):
        bg = WHITE if ri % 2 == 0 else (246, 248, 250)
        cx = x
        for i, val in enumerate(row):
            d.rectangle([cx, ry, cx + colw[i], ry + rowh], fill=bg)
            d.line([cx, ry, cx, ry + rowh], fill=LGRAY, width=1)
            txt(d, cx + 6, ry + rowh / 2, str(val), fs - 1, TXT, anchor="lm")
            cx += colw[i]
        d.line([x, ry + rowh, x + total, ry + rowh], fill=LGRAY, width=1)
        ry += rowh
    # outer border
    d.rectangle([x, y, x + total, ry], outline=BORDER, width=1)
    return ry

def schematic_tag(d, W, H):
    txt(d, W - 10, H - 12, "示意 · 待替换为真实截图", 9, (170, 175, 182), anchor="rm")

# ---------- app shell ----------
def app_shell(title, nav, active, content_fn, cw=940, ch=680, role="管理员: admin"):
    W = 220 + cw
    sbh = 28
    H = 46 + ch + sbh
    img = Image.new("RGB", (W, H), (236, 238, 241))
    d = ImageDraw.Draw(img)
    # title bar
    d.rectangle([0, 0, W, 46], fill=DARK)
    txt(d, 16, 23, title, 16, WHITE, bold=True, anchor="lm")
    txt(d, W - 96, 23, role, 11, (200, 204, 210), anchor="rm")
    btn(d, W - 84, 9, 72, 28, "退出系统", (70, 75, 82), size=12, radius=3)
    # left nav
    d.rectangle([0, 46, 220, H - sbh], fill=DARK)
    txt(d, 18, 64, "NAVIGATION 导航菜单", 11, (150, 155, 162), bold=True, anchor="lm")
    ny = 94
    for item in nav:
        is_a = (item == active)
        d.rectangle([10, ny, 210, ny + 44], fill=(DARK2 if is_a else DARK))
        if is_a:
            d.rectangle([10, ny, 15, ny + 44], fill=BLUE)
        txt(d, 28, ny + 22, item, 13, (WHITE if is_a else (200, 204, 210)), bold=is_a, anchor="lm")
        ny += 52
    # content
    content_fn(d, 220, 46, cw, ch)
    # status bar
    sy = H - sbh
    d.rectangle([0, sy, W, sy + sbh], fill=(238, 240, 243))
    d.line([0, sy, W, sy], fill=(210, 214, 220), width=1)
    txt(d, 12, sy + 14, "Ready 系统就绪", 10, (90, 95, 100), anchor="lm")
    txt(d, W - 12, sy + 14, "软件目录: D:\\git\\zc\\MS.ExamSystem   |   知识库已同步 (2026-08-18 09:30)", 10, (90, 95, 100), anchor="rm")
    schematic_tag(d, W, H)
    return img

def content_title(d, x, y, w, title, sub=None):
    txt(d, x + 24, y + 24, title, 18, TXT, bold=True, anchor="lm")
    if sub:
        txt(d, x + 24, y + 50, sub, 11, GRAY, anchor="lm")

# ---------- 6-1 dashboard ----------
def dash_content(d, x, y, w, h):
    content_title(d, x, y, w, "管理端首页 / Dashboard", "数据统计总览与快捷入口")
    # stat cards
    cards = [("故障类型数", "18", BLUE), ("已分类案例数", "126", GREEN),
             ("知识库文件数", "34", ORANGE), ("累计考试场次", "52", PURPLE)]
    cw = 205; chh = 110; gap = 18; sx = x + 24
    for i, (lab, num, col) in enumerate(cards):
        cx = sx + i * (cw + gap)
        cy = y + 74
        rr(d, [cx, cy, cx + cw, cy + chh], 8, fill=WHITE, outline=BORDER, width=1)
        d.rectangle([cx, cy, cx + cw, cy + 6], fill=col)
        txt(d, cx + cw / 2, cy + 50, num, 34, col, bold=True, anchor="mm")
        txt(d, cx + cw / 2, cy + 88, lab, 13, TXT, anchor="mm")
    # quick entries
    txt(d, x + 24, y + 210, "快捷入口", 15, TXT, bold=True, anchor="lm")
    q = [("新增故障类型", GREEN), ("上传故障案例", BLUE), ("导入知识库文件", ORANGE), ("导出考试统计", PURPLE)]
    for i, (lab, col) in enumerate(q):
        cx = sx + i * (cw + gap)
        cy = y + 244
        rr(d, [cx, cy, cx + cw, cy + 120], 8, fill=WHITE, outline=BORDER, width=1)
        rr(d, [cx + cw / 2 - 26, cy + 18, cx + cw / 2 + 26, cy + 70], 30, fill=col)
        txt(d, cx + cw / 2, cy + 44, "+", 30, WHITE, bold=True, anchor="mm")
        txt(d, cx + cw / 2, cy + 98, lab, 13, TXT, anchor="mm")

# ---------- 6-2 fault type manage ----------
def fault_type_content(d, x, y, w, h):
    content_title(d, x, y, w, "故障类型管理", "维护设备 / 故障的分类目录（中英文名称、描述）")
    # toolbar
    ty = y + 70
    txt(d, x + 24, ty + 14, "搜索：", 12, TXT, anchor="lm")
    field(d, x + 70, ty, 180, 28, placeholder="输入关键词")
    btn(d, x + 258, ty, 64, 28, "搜索", DARK, size=12)
    btn(d, x + 330, ty, 64, 28, "添加", GREEN, size=12)
    btn(d, x + 400, ty, 64, 28, "编辑", BLUE, size=12)
    btn(d, x + 470, ty, 64, 28, "删除", RED, size=12)
    grid(d, x + 24, ty + 48,
         ["编号", "类型名称", "英文名称", "描述", "创建时间"],
         [["FT001", "轴承类故障", "Bearing", "滚动轴承磨损/剥落类", "2026-08-10 09:12"],
          ["FT002", "密封类故障", "Sealing", "油封/密封圈老化渗漏", "2026-08-10 09:15"],
          ["FT003", "电气类故障", "Electrical", "接线松动/短路/过载", "2026-08-11 14:03"],
          ["FT004", "润滑类故障", "Lubrication", "润滑不足/油脂变质", "2026-08-11 14:20"],
          ["FT005", "紧固件类故障", "Fastener", "螺栓松动/脱落", "2026-08-12 10:41"]],
         [70, 160, 130, 300, 158], rowh=34)

# ---------- 6-3 fault case manage ----------
def example_card(d, x, y, w=270, h=185, tag="轴承磨损", time="2026-08-10 14:22"):
    rr(d, [x, y, x + w, y + h], 6, fill=WHITE, outline=BORDER, width=1)
    d.rectangle([x + 1, y + 1, x + w - 1, y + 130], fill=(225, 228, 233))
    txt(d, x + w / 2, y + 65, "案例图片", 13, (150, 155, 162), anchor="mm")
    tw = len(tag) * 13 + 18
    rr(d, [x + 12, y + 140, x + 12 + tw, y + 162], 4, fill=GTAG)
    txt(d, x + 12 + tw / 2, y + 151, tag, 11, WHITE, anchor="mm")
    txt(d, x + 12, y + 172, time, 10, GRAY, anchor="lm")

def tree_panel(d, x, y, w, h, title="全部故障类型", nodes=None):
    d.rectangle([x, y, x + w, y + h], fill=(250, 251, 252), outline=BORDER, width=1)
    d.rectangle([x, y, x + w, y + 30], fill=(236, 239, 243))
    txt(d, x + 12, y + 15, title, 12, TXT, bold=True, anchor="lm")
    ny = y + 44
    for n in (nodes or []):
        indent = n.get("indent", 0)
        checked = n.get("checked", True)
        # checkbox
        bx = x + 12 + indent
        d.rectangle([bx, ny - 7, bx + 14, ny + 7], outline=(150, 156, 164), width=1)
        if checked:
            txt(d, bx + 7, ny, "√", 12, BLUE, bold=True, anchor="mm")
        txt(d, bx + 22, ny, n["label"], 12, TXT, anchor="lm")
        ny += 26

def fault_case_content(d, x, y, w, h, admin=True):
    content_title(d, x, y, w, "故障案例管理" if admin else "故障案例库",
                  "左侧故障类型树，右侧案例卡片列表")
    split = 222
    tree_panel(d, x + 24, y + 70, split - 24, h - 100,
               nodes=[{"label": "全部故障类型", "checked": False},
                      {"label": "轴承类故障", "indent": 18},
                      {"label": "密封类故障", "indent": 18},
                      {"label": "电气类故障", "indent": 18},
                      {"label": "润滑类故障", "indent": 18},
                      {"label": "紧固件类故障", "indent": 18}])
    rx = x + 24 + split
    rw = w - split - 48
    # tool panel
    ty = y + 70
    d.rectangle([rx, ty, rx + rw, ty + 40], fill=(248, 249, 251), outline=BORDER, width=1)
    txt(d, rx + 14, ty + 20, "当前类型：全部", 12, TXT, anchor="lm")
    if admin:
        btn(d, rx + rw - 210, ty + 6, 60, 28, "添加", GREEN, size=12)
        btn(d, rx + rw - 144, ty + 6, 60, 28, "编辑", BLUE, size=12)
        btn(d, rx + rw - 78, ty + 6, 60, 28, "删除", RED, size=12)
    # cards
    tags = ["轴承磨损", "油封渗漏", "接线松动", "润滑不足", "螺栓松动", "绝缘老化"]
    times = ["2026-08-10 14:22", "2026-08-10 15:10", "2026-08-11 09:30",
             "2026-08-11 16:05", "2026-08-12 11:20", "2026-08-12 14:48"]
    cw = 270; gap = 18; per_row = 2
    for i in range(4):
        col = i % per_row
        rowi = i // per_row
        cx = rx + col * (cw + gap)
        cy = ty + 56 + rowi * (185 + 18)
        example_card(d, cx, cy, w=cw, h=185, tag=tags[i], time=times[i])

# ---------- 6-4 exam manage ----------
def exam_manage_content(d, x, y, w, h):
    content_title(d, x, y, w, "考试考核管理", "配置考试场次（类型、题量、时长、分值、及格线）")
    ty = y + 70
    btn(d, x + 24, ty, 72, 28, "新增", GREEN, size=12)
    btn(d, x + 104, ty, 72, 28, "删除", RED, size=12)
    grid(d, x + 24, ty + 48,
         ["ID", "考试名称", "考试类型", "题目数量", "及格分数", "每题分值", "考试时长", "创建时间", "操作"],
         [["1", "月度目视考核-8月", "标准化测试", "10", "60", "10", "30", "2026-08-01 10:00", "编辑"],
          ["2", "轴承专项测试", "专项测试", "15", "70", "10", "45", "2026-08-05 14:20", "编辑"],
          ["3", "新员工基础测试", "基础测试", "20", "60", "5", "60", "2026-08-08 09:30", "编辑"],
          ["4", "理论综合测试", "理论测试", "25", "75", "4", "90", "2026-08-10 16:00", "编辑"],
          ["5", "实操识别测试", "实践测试", "12", "72", "8", "40", "2026-08-12 11:00", "编辑"]],
         [44, 190, 110, 74, 74, 74, 74, 150, 60], rowh=32, fs=10)

# ---------- 6-5 system manage ----------
def system_manage_content(d, x, y, w, h):
    content_title(d, x, y, w, "系统管理", "角色权限 / 软件公告 / 数据同步说明 / 用户管理")
    tx = x + 24; ty = y + 70; tw = w - 48
    tabs = ["角色权限", "软件公告", "数据同步说明", "用户管理"]
    active = 0
    twt = tw / len(tabs)
    for i, t in enumerate(tabs):
        bx = tx + i * twt
        is_a = (i == active)
        d.rectangle([bx, ty, bx + twt, ty + 34], fill=(DARK if is_a else (230, 233, 238)))
        txt(d, bx + twt / 2, ty + 17, t, 12, (WHITE if is_a else TXT), bold=is_a, anchor="mm")
    # body
    by = ty + 34
    d.rectangle([tx, by, tx + tw, by + h - 110 - 34], fill=WHITE, outline=BORDER, width=1)
    # matrix
    mods = ["故障类型管理", "故障案例管理", "知识库管理", "考试考核管理", "系统管理", "在线考试"]
    rows = []
    for m in mods:
        rows.append([m, "√", "√", "√"])  # admin
    # operator: some, student: few
    op = ["√", "√", "√", "√", "×", "×"]
    st = ["×", "√", "√", "×", "×", "√"]
    data = []
    for i, m in enumerate(mods):
        data.append([m, "√", op[i], st[i]])
    grid(d, tx + 20, by + 20, ["功能模块", "管理员", "普通操作员", "学生"],
         data, [260, 150, 150, 150], rowh=34, fs=12)
    txt(d, tx + 20, by + 280, "（√ = 允许访问，× = 禁止访问；修改后点击“保存”）", 10, GRAY, anchor="lm")

# ---------- 7-1 student home ----------
def student_home_content(d, x, y, w, h):
    content_title(d, x, y, w, "学生首页", "欢迎信息、公告通知与最近成绩")
    # welcome panel (dark)
    wpw = w - 48
    d.rectangle([x + 24, y + 70, x + 24 + wpw, y + 200], fill=DARK)
    txt(d, x + 48, y + 110, "欢迎回来，王机务学员", 20, WHITE, bold=True, anchor="lm")
    txt(d, x + 48, y + 150, "学号: 2024秋季机务01班   |   累计学时: 24.5h", 13, (200, 204, 210), anchor="lm")
    # notice panel (right)
    nx = x + 24 + wpw - 320
    d.rectangle([nx, y + 220, nx + 320, y + 470], fill=WHITE, outline=BORDER, width=1)
    d.rectangle([nx, y + 220, nx + 320, y + 252], fill=(236, 239, 243))
    txt(d, nx + 14, y + 236, "公告通知", 13, TXT, bold=True, anchor="lm")
    notices = ["① 8月月度目视考核将于8月25日开启", "② 轴承类案例库已更新12条", "③ 知识库新增《设备维护手册》"]
    ny = y + 272
    for ntext in notices:
        txt(d, nx + 14, ny, ntext, 11, TXT, anchor="lm")
        ny += 46
    # score panel (left)
    sx = x + 24
    d.rectangle([sx, y + 220, sx + (wpw - 340), y + 470], fill=WHITE, outline=BORDER, width=1)
    d.rectangle([sx, y + 220, sx + (wpw - 340), y + 252], fill=(236, 239, 243))
    txt(d, sx + 14, y + 236, "最近成绩表现", 13, TXT, bold=True, anchor="lm")
    scores = [("月度目视考核-7月", "82"), ("轴承专项测试", "75"), ("新员工基础测试", "90"), ("理论综合测试", "68")]
    cw = (wpw - 340 - 48) / 2
    for i, (lab, sc) in enumerate(scores):
        col = i % 2; r = i // 2
        cx = sx + 14 + col * (cw + 20)
        cy = y + 270 + r * 92
        rr(d, [cx, cy, cx + cw, cy + 76], 6, fill=LGBG)
        txt(d, cx + cw / 2, cy + 28, sc + "分", 22, BLUE, bold=True, anchor="mm")
        txt(d, cx + cw / 2, cy + 60, lab, 11, TXT, anchor="mm")

# ---------- 7-3 knowledge learning ----------
def knowledge_content(d, x, y, w, h):
    content_title(d, x, y, w, "知识库学习", "以文件卡片展示知识库资料，双击打开预览")
    # file cards (left)
    files = [("设备维护手册.pdf", "2.4 MB", "2026-08-01"), ("轴承图谱.docx", "1.1 MB", "2026-08-03"),
             ("密封标准.pdf", "3.0 MB", "2026-08-05"), ("电气接线图.png", "0.8 MB", "2026-08-07")]
    fw = 220; fh = 170; gap = 18
    leftw = 500
    for i, (nm, sz, tm) in enumerate(files):
        col = i % 2; r = i // 2
        cx = x + 24 + col * (fw + gap)
        cy = y + 80 + r * (fh + 18)
        rr(d, [cx, cy, cx + fw, cy + fh], 6, fill=WHITE, outline=BORDER, width=1)
        rr(d, [cx + fw / 2 - 26, cy + 16, cx + fw / 2 + 26, cy + 68], 6, fill=ORANGE)
        txt(d, cx + fw / 2, cy + 42, "PDF", 16, WHITE, bold=True, anchor="mm")
        txt(d, cx + fw / 2, cy + 100, nm, 12, TXT, bold=True, anchor="mm")
        txt(d, cx + 12, cy + 140, sz, 10, GRAY, anchor="lm")
        txt(d, cx + fw - 12, cy + 140, tm, 10, GRAY, anchor="rm")
    # preview panel (right)
    px = x + 24 + leftw + 20
    pw = w - leftw - 68
    d.rectangle([px, y + 80, px + pw, y + h - 40], fill=WHITE, outline=BORDER, width=1)
    d.rectangle([px, y + 80, px + pw, y + 116], fill=(236, 239, 243))
    btn(d, px + 14, y + 88, 56, 24, "返回", (150, 156, 164), size=11)
    txt(d, px + 90, y + 98, "设备维护手册.pdf", 12, TXT, bold=True, anchor="lm")
    d.rectangle([px + 12, y + 128, px + pw - 12, y + h - 56], fill=(245, 246, 248), outline=LGRAY, width=1)
    txt(d, px + pw / 2, y + (h - 56 + 128) / 2, "（文件预览区 · 调用默认程序打开）", 12, GRAY, anchor="mm")

# ---------- 7-4 exam records ----------
def exam_records_content(d, x, y, w, h):
    content_title(d, x, y, w, "我的考试记录", "查看考试得分、总分，点击“查看详情”逐题解析")
    ty = y + 70
    btn(d, x + 24, ty, 96, 28, "导出明细", BLUE, size=12)
    grid(d, x + 24, ty + 46,
         ["考试名称", "考生", "考试时间", "得分", "总分", "操作"],
         [["月度目视考核-7月", "王机务", "2026-07-30 10:20", "82", "100", "查看详情"],
          ["轴承专项测试", "王机务", "2026-08-05 15:00", "75", "100", "查看详情"],
          ["新员工基础测试", "王机务", "2026-08-08 09:50", "90", "100", "查看详情"],
          ["理论综合测试", "王机务", "2026-08-10 16:30", "68", "100", "查看详情"]],
         [220, 120, 180, 100, 100, 110], rowh=32, fs=10)
    # detail box
    dy = ty + 46 + 4 * 32 + 24
    d.rectangle([x + 24, dy, x + 24 + w - 48, dy + 150], fill=(250, 251, 252), outline=BORDER, width=1)
    txt(d, x + 40, dy + 16, "考试记录详情  月度目视考核-7月  |  考试时间 2026-07-30 10:20  |  得分 82 / 100", 11, TXT, bold=True, anchor="lm")
    grid(d, x + 40, dy + 40,
         ["题号", "故障类型", "正确答案", "我的答案", "结果"],
         [["1", "轴承磨损", "轴承磨损", "轴承磨损", "正确"],
          ["2", "油封渗漏", "油封渗漏", "接线松动", "错误"],
          ["3", "接线松动", "接线松动", "接线松动", "正确"]],
         [60, 180, 150, 150, 110], rowh=28, fs=10)

# ---------- 8-1 test page ----------
def test_page_content(d, x, y, w, h):
    # page title
    txt(d, x + 24, y + 24, "在线考试考核", 18, TXT, bold=True, anchor="lm")
    rr(d, [x + w - 200, y + 14, x + w - 24, y + 44], 4, fill=(255, 235, 235))
    txt(d, x + w - 112, y + 29, "剩余时间: 12:30", 14, RED, bold=True, anchor="mm")
    # left 题目导航
    nvw = 170
    d.rectangle([x + 24, y + 70, x + 24 + nvw, y + h - 40], fill=WHITE, outline=BORDER, width=1)
    d.rectangle([x + 24, y + 70, x + 24 + nvw, y + 100], fill=BLUE)
    txt(d, x + 24 + nvw / 2, y + 85, "题目导航", 13, WHITE, bold=True, anchor="mm")
    for i in range(10):
        col = i % 2; r = i // 2
        bx = x + 24 + 20 + col * 64
        by = y + 120 + r * 46
        # answered green, current blue
        if i == 2:
            rr(d, [bx, by, bx + 44, by + 36], 6, fill=BLUE)
            txt(d, bx + 22, by + 18, str(i + 1), 14, WHITE, bold=True, anchor="mm")
        elif i in (0, 1, 3, 4, 5):
            rr(d, [bx, by, bx + 44, by + 36], 6, fill=GREEN)
            txt(d, bx + 22, by + 18, str(i + 1), 14, WHITE, bold=True, anchor="mm")
        else:
            rr(d, [bx, by, bx + 44, by + 36], 6, fill=WHITE, outline=BORDER, width=1)
            txt(d, bx + 22, by + 18, str(i + 1), 14, TXT, anchor="mm")
    # right content
    rx = x + 24 + nvw + 20
    rw = w - nvw - 68
    # image panel
    d.rectangle([rx, y + 70, rx + rw, y + 290], fill=(225, 228, 233), outline=BORDER, width=1)
    txt(d, rx + rw / 2, y + 180, "故障案例图片", 14, (150, 155, 162), anchor="mm")
    # question panel
    qy = y + 310
    d.rectangle([rx, qy, rx + rw, qy + 180], fill=WHITE, outline=BORDER, width=1)
    txt(d, rx + 16, qy + 18, "第 3 题 / 共 10 题", 13, BLUE, bold=True, anchor="lm")
    txt(d, rx + 16, qy + 48, "3. 请识别图片中的故障类型：", 14, TXT, bold=True, anchor="lm")
    opts = ["A. 轴承磨损", "B. 油封渗漏", "C. 接线松动", "D. 润滑不足"]
    oy = qy + 82
    for opt in opts:
        d.rectangle([rx + 16, oy - 9, rx + 28, oy + 3], outline=(150, 156, 164), width=1)
        txt(d, rx + 38, oy, opt, 13, TXT, anchor="lm")
        oy += 26
    # bottom buttons
    by = y + h - 56
    btn(d, rx, by, 110, 34, "← 上一题", (150, 156, 164), size=13)
    btn(d, rx + 124, by, 110, 34, "下一题 →", (150, 156, 164), size=13)
    btn(d, rx + rw - 130, by, 130, 34, "提交考试", GREEN, size=13)

# ---------- login dialog ----------
def login_dialog():
    W, H = 470, 440
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    # title bar
    d.rectangle([0, 0, W, 52], fill=DARK)
    txt(d, W / 2, 26, "目视案例库软件系统", 18, WHITE, bold=True, anchor="mm")
    btn(d, W - 96, 12, 84, 28, "English", (70, 75, 82), size=11)
    # big title
    txt(d, W / 2, 96, "用户登录", 16, TXT, bold=True, anchor="mm")
    # form
    lx = 56; ix = 140; iw = 274
    fy = 140; step = 56
    txt(d, lx, fy + 14, "角色", 13, TXT, anchor="lm")
    field(d, ix, fy, iw, 32, text="学生")
    # dropdown arrow
    d.polygon([(ix + iw - 20, fy + 13), (ix + iw - 12, fy + 13), (ix + iw - 16, fy + 19)], fill=GRAY)
    txt(d, lx, fy + step + 14, "账号", 13, TXT, anchor="lm")
    field(d, ix, fy + step, iw, 32, text="1")
    txt(d, lx, fy + 2 * step + 14, "密码", 13, TXT, anchor="lm")
    field(d, ix, fy + 2 * step, iw, 32, text="••••")
    # login button
    btn(d, ix, fy + 3 * step, iw, 40, "登 录", BLUE, size=15)
    # register / exit
    txt(d, ix, fy + 3 * step + 58, "学生注册", 12, BLUE, anchor="lm")
    txt(d, ix + iw, fy + 3 * step + 58, "退出", 12, GRAY, anchor="rm")
    # version
    txt(d, W / 2, H - 18, "Version V1.0", 10, GRAY, anchor="mm")
    schematic_tag(d, W, H)
    return img

# ---------- generate ----------
def main():
    admin_nav = ["管理首页", "故障类型管理", "故障案例管理", "知识库管理", "考试考核管理", "系统管理"]
    student_nav = ["学生首页", "故障案例库", "知识库学习", "在线考试", "我的考试记录"]

    imgs = {}
    # 2-1 & 5-1 login
    login = login_dialog()
    imgs["2-1"] = login
    imgs["5-1"] = login
    # 6-1 dashboard
    imgs["6-1"] = app_shell("目视案例库软件系统", admin_nav, "管理首页", dash_content, role="管理员: admin")
    # 6-2 fault type
    imgs["6-2"] = app_shell("目视案例库软件系统", admin_nav, "故障类型管理", fault_type_content, role="管理员: admin")
    # 6-3 fault case
    imgs["6-3"] = app_shell("目视案例库软件系统", admin_nav, "故障案例管理",
                            lambda d, x, y, w, h: fault_case_content(d, x, y, w, h, admin=True), role="管理员: admin")
    # 6-4 exam manage
    imgs["6-4"] = app_shell("目视案例库软件系统", admin_nav, "考试考核管理", exam_manage_content, role="管理员: admin")
    # 6-5 system manage
    imgs["6-5"] = app_shell("目视案例库软件系统", admin_nav, "系统管理", system_manage_content, role="管理员: admin")
    # 7-1 student home
    imgs["7-1"] = app_shell("目视案例库软件系统", student_nav, "学生首页", student_home_content, role="学生: 王机务学员")
    # 7-2 fault case library (student)
    imgs["7-2"] = app_shell("目视案例库软件系统", student_nav, "故障案例库",
                            lambda d, x, y, w, h: fault_case_content(d, x, y, w, h, admin=False), role="学生: 王机务学员")
    # 7-3 knowledge
    imgs["7-3"] = app_shell("目视案例库软件系统", student_nav, "知识库学习", knowledge_content, role="学生: 王机务学员")
    # 7-4 exam records
    imgs["7-4"] = app_shell("目视案例库软件系统", student_nav, "我的考试记录", exam_records_content, role="学生: 王机务学员")
    # 8-1 test page
    imgs["8-1"] = app_shell("目视案例库软件系统", student_nav, "在线考试", test_page_content, role="学生: 王机务学员")

    for k, im in imgs.items():
        path = os.path.join(OUT, f"fig_{k.replace('-', '_')}.png")
        im.save(path, "PNG")
        print("saved", path, im.size)

if __name__ == "__main__":
    main()
