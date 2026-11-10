# -*- coding: utf-8 -*-
"""
生成「城市计算之对轻微犯罪的数据库」中期汇报 PPT(10 页, 16:9)。
运行: python build_ppt.py
输出: 中期汇报_城市犯罪数据库.pptx
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pptx_lib"))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE

# ---------- 主题色 ----------
DARK   = RGBColor(0x1F, 0x38, 0x64)   # 深蓝
BLUE   = RGBColor(0x2B, 0x6C, 0xB0)   # 主蓝
ACCENT = RGBColor(0xE7, 0x4C, 0x3C)   # 红(犯罪)
GREEN  = RGBColor(0x2E, 0xCC, 0x71)
ORANGE = RGBColor(0xE6, 0x7E, 0x22)
GRAY   = RGBColor(0x3D, 0x3D, 0x3D)
MIDGRAY= RGBColor(0x7F, 0x8C, 0x8D)
LIGHT  = RGBColor(0xF2, 0xF4, 0xF7)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Microsoft YaHei"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def add_rect(slide, x, y, w, h, color):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def add_text(slide, x, y, w, h, text, size=18, color=GRAY, bold=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.name = FONT
    return tb


def add_bullets(slide, x, y, w, h, items, size=17, color=GRAY):
    """items: list of (text, level) 或 str"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for it in items:
        if isinstance(it, tuple):
            text, lvl = it
        else:
            text, lvl = it, 0
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = text
        p.level = lvl
        p.space_after = Pt(9)
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.name = FONT
    return tb


def title_bar(slide, text, kicker=None):
    add_rect(slide, 0, 0, 13.333, 1.02, DARK)
    add_rect(slide, 0, 1.02, 13.333, 0.06, ACCENT)
    add_text(slide, 0.55, 0.14, 11.5, 0.75, text, size=26, color=WHITE, bold=True,
             anchor=MSO_ANCHOR.MIDDLE)
    if kicker:
        add_text(slide, 11.2, 0.3, 1.9, 0.4, kicker, size=12, color=RGBColor(0xBB, 0xC8, 0xDD),
                 align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def footer(slide, idx):
    add_text(slide, 12.4, 7.05, 0.7, 0.35, str(idx), size=11, color=MIDGRAY,
             align=PP_ALIGN.RIGHT)


# ==================================================================
# 1. 封面
# ==================================================================
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, 13.333, 7.5, DARK)
add_rect(s, 0, 4.72, 13.333, 0.05, ACCENT)
add_text(s, 1.0, 1.5, 11.3, 0.6, "数据库应用开发 · 中期汇报", size=20, color=RGBColor(0x9F, 0xB3, 0xD1))
add_text(s, 1.0, 2.15, 11.3, 1.9, "城市计算之对轻微犯罪的数据库",
         size=44, color=WHITE, bold=True)
add_text(s, 1.0, 3.75, 11.3, 0.8,
         "基于英国 data.police.uk 真实数据的时空数据库设计与可视化",
         size=20, color=RGBColor(0xCF, 0xDA, 0xE8))
add_text(s, 1.0, 5.1, 11.3, 1.4,
         "姓    名：朱了凡\n学    号：2451027\n专    业：计算机",
         size=16, color=RGBColor(0xCF, 0xDA, 0xE8))

# ==================================================================
# 2. 项目背景与目标
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "项目背景与目标", "02")
add_text(s, 0.55, 1.35, 12.2, 0.5, "背景：城市计算 × 轻微犯罪", size=20, color=BLUE, bold=True)
add_bullets(s, 0.55, 1.95, 12.2, 2.6, [
    "•  城市计算(Urban Computing)通过多源异构数据理解城市动态，犯罪数据是典型的高频时空数据",
    "•  轻微犯罪(盗窃、扰序、毁财)具有高频、广域、累积效应显著的特点，时空异质性突出",
    "•  因此数据库必须原生支持「时间 + 空间」维度的存储、索引与查询，而非简单附加坐标",
], size=17)
add_text(s, 0.55, 4.55, 12.2, 0.5, "目标与思路", size=20, color=BLUE, bold=True)
add_bullets(s, 0.55, 5.1, 12.2, 1.8, [
    "•  用真实公开数据构建一个面向城市计算时空分析的关系数据库",
    "•  三步走：数据源选型 → ER 与数据库设计 → 可视化 Web 应用",
    "•  全部数据真实可溯源，全链路可在本机复现",
], size=17)
footer(s, 2)

# ==================================================================
# 3. 数据来源调研与选择
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "数据来源调研与选择", "03")
add_text(s, 0.55, 1.3, 12.2, 0.5, "候选数据源对比(重点关注与地理位置强相关的逐案数据)", size=18, color=BLUE, bold=True)

rows = [
    ("数据源", "含经纬度", "含处罚结果", "国内直连"),
    ("中国城市级逐案犯罪数据", "—(不公开)", "—", "—"),
    ("美国·芝加哥 Crimes 2001+", "✓", "✗(仅是否逮捕)", "✗ 403 被墙"),
    ("英国·data.police.uk", "✓", "✓(警告/罚款/社区判决等)", "✓ 实测可达"),
]
tbl = s.shapes.add_table(4, 4, Inches(0.55), Inches(1.9), Inches(12.2), Inches(2.6)).table
tbl.columns[0].width = Inches(4.6)
tbl.columns[1].width = Inches(2.4)
tbl.columns[2].width = Inches(3.4)
tbl.columns[3].width = Inches(1.8)
for ri, row in enumerate(rows):
    for ci, val in enumerate(row):
        c = tbl.cell(ri, ci)
        c.text = val
        c.margin_top = Pt(4); c.margin_bottom = Pt(4)
        p = c.text_frame.paragraphs[0]
        p.font.name = FONT
        p.font.size = Pt(15)
        if ri == 0:
            p.font.bold = True
            p.font.color.rgb = WHITE
            c.fill.solid(); c.fill.fore_color.rgb = BLUE
        elif ri == 3:
            c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xE8, 0xF4, 0xE8)
            p.font.color.rgb = GRAY
        else:
            c.fill.solid(); c.fill.fore_color.rgb = LIGHT if ri % 2 else WHITE
            p.font.color.rgb = GRAY
add_text(s, 0.55, 4.85, 12.2, 1.9,
         "结论：选择英国 data.police.uk\n"
         "① 国内网络实测可达(芝加哥 Socrata 被墙)；② 除经纬度外还带「处理结果(处罚方式)」，正好对应轻微犯罪的处罚维度；\n"
         "③ 天生不含姓名/身份证号，满足个人信息保护合规；④ 类别(扰序/盗窃/毁财/涉车)与轻微犯罪主题高度吻合。",
         size=16, color=GRAY)
footer(s, 3)

# ==================================================================
# 4. 数据获取
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "数据获取", "04")
add_bullets(s, 0.55, 1.4, 12.2, 2.0, [
    "•  范围：英国·利兹(Leeds)市区及近郊，2024 年 1–6 月",
    "•  方法：官方 Crimes-at-street API，按经纬度网格化多边形分块抓取 + 指数退避重试 + 断点续传 + 去重",
    "•  成果：37,811 条街道级犯罪记录(原始 CSV 7.4MB，JSONL 15.6MB)",
], size=17)
# 4 个指标卡
cards = [
    ("37,811", "犯罪记录总数", BLUE),
    ("100%", "含经纬度", GREEN),
    ("14 类", "犯罪类别", ORANGE),
    ("93.7%", "有处理结果", ACCENT),
]
cx = 0.55
for num, lab, col in cards:
    add_rect(s, cx, 3.7, 2.85, 1.5, LIGHT)
    add_rect(s, cx, 3.7, 2.85, 0.09, col)
    add_text(s, cx, 3.95, 2.85, 0.7, num, size=30, color=col, bold=True, align=PP_ALIGN.CENTER)
    add_text(s, cx, 4.68, 2.85, 0.4, lab, size=14, color=MIDGRAY, align=PP_ALIGN.CENTER)
    cx += 3.05
add_text(s, 0.55, 5.55, 12.2, 1.3,
         "时间分布(逐月)：1 月 5980 · 2 月 5622 · 3 月 6296 · 4 月 6377 · 5 月 6903 · 6 月 6633",
         size=15, color=MIDGRAY)
footer(s, 4)

# ==================================================================
# 5. ER 图设计(方案A)
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "ER 图设计 —— 方案 A：收敛到时空核心", "05")
add_text(s, 0.55, 1.25, 12.2, 0.45, "星型模型：fact_crime(案件) 关联 4 个维度，地点再上卷到两级地理层级", size=16, color=MIDGRAY)

def box(x, y, w, h, text, fill=BLUE):
    add_rect(s, x, y, w, h, fill)
    add_text(s, x, y, w, h, text, size=14, color=WHITE, bold=True,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

def arrow(x1, y1, x2, y2):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = MIDGRAY
    c.line.width = Pt(1.5)

box(5.17, 1.75, 3.0, 0.8, "dim_time 时间维度")
box(1.25, 3.35, 2.7, 0.8, "dim_category 类别")
box(5.17, 3.35, 3.0, 1.0, "fact_crime\n案件记录(时空事件)", DARK)
box(9.4, 3.35, 2.7, 0.8, "dim_outcome 处理结果")
box(5.17, 5.05, 3.0, 0.8, "dim_location 地点(经纬度)")
box(5.17, 6.25, 3.0, 0.7, "dim_neighbourhood 社区")
box(9.0, 6.25, 3.0, 0.7, "dim_force 警署")

arrow(6.67, 2.55, 6.67, 3.35)
arrow(3.95, 3.85, 5.17, 3.85)
arrow(8.17, 3.85, 9.4, 3.85)
arrow(6.67, 4.35, 6.67, 5.05)
arrow(6.67, 5.85, 6.67, 6.25)
arrow(8.17, 6.6, 9.0, 6.6)
add_text(s, 5.17, 7.05, 3.0, 0.35, "社区 → 警署", size=12, color=MIDGRAY, align=PP_ALIGN.CENTER)
footer(s, 5)

# ==================================================================
# 6. 逻辑设计(3NF)
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "逻辑设计与规范化", "06")
rows = [
    ("表", "主键", "说明"),
    ("dim_force 警署", "force_id", "部门/辖区(44 个)"),
    ("dim_neighbourhood 社区", "neighbourhood_id", "FK→警署(21 个)"),
    ("dim_location 地点", "location_id", "街道+经纬度, FK→社区"),
    ("dim_time 时间", "time_id", "月份/年/季/季"),
    ("dim_category 类别", "category_id", "14 类 + 轻微犯罪分级"),
    ("dim_outcome 处理结果", "outcome_id", "处罚型/终止型/未决型"),
    ("fact_crime 案件", "crime_id", "事实表, FK→四个维度"),
]
tbl = s.shapes.add_table(8, 3, Inches(0.55), Inches(1.4), Inches(7.2), Inches(4.9)).table
tbl.columns[0].width = Inches(3.4)
tbl.columns[1].width = Inches(1.7)
tbl.columns[2].width = Inches(2.1)
for ri, row in enumerate(rows):
    for ci, val in enumerate(row):
        c = tbl.cell(ri, ci)
        c.text = val
        c.margin_top = Pt(3); c.margin_bottom = Pt(3)
        p = c.text_frame.paragraphs[0]
        p.font.name = FONT; p.font.size = Pt(13)
        if ri == 0:
            p.font.bold = True; p.font.color.rgb = WHITE
            c.fill.solid(); c.fill.fore_color.rgb = BLUE
        elif ri == 7:
            c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xE8, 0xF0, 0xFB)
            p.font.color.rgb = DARK
        else:
            c.fill.solid(); c.fill.fore_color.rgb = LIGHT if ri % 2 else WHITE
            p.font.color.rgb = GRAY
add_text(s, 8.05, 1.4, 4.8, 0.45, "轻微犯罪分级(14 类 → 4 级)", size=16, color=BLUE, bold=True)
add_bullets(s, 8.05, 1.9, 4.8, 3.2, [
    "•  轻微：扰序/盗窃/行窃等",
    "•  一般：涉车/毁财/扒窃",
    "•  较重：入室盗窃/毒品/持械",
    "•  严重：抢劫/暴力犯罪",
], size=14)
add_text(s, 8.05, 5.1, 4.8, 0.45, "处理结果三类", size=16, color=BLUE, bold=True)
add_bullets(s, 8.05, 5.55, 4.8, 1.6, [
    "•  处罚型：警告/罚款通知/社区判决/调解",
    "•  终止型：无法起诉/无嫌疑人",
    "•  未决型：调查中/待法院判决",
], size=14)
add_text(s, 0.55, 6.5, 12.2, 0.5, "全部 7 张表满足 3NF，无部分依赖、无传递依赖。", size=15, color=MIDGRAY)
footer(s, 6)

# ==================================================================
# 7. 数据库实现
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "数据库实现", "07")
add_text(s, 0.55, 1.35, 12.2, 0.5, "MySQL 8.0 建库脚本 + 索引 + 视图(sql/schema_mysql.sql)", size=18, color=BLUE, bold=True)
add_bullets(s, 0.55, 1.95, 12.2, 2.6, [
    "•  7 张表：主键自动聚簇索引 + 全部外键手动建索引 + 业务索引(类别/分级/结果类型/经纬度组合)",
    "•  坐标以 DECIMAL(10,7) 存储，不依赖 PostGIS；半径查询用平方距离公式",
    "•  4 个视图：案件全景 / 月度统计 / 社区治安热点 / 脱敏视图(面向研究开放)",
], size=16)
add_text(s, 0.55, 4.6, 12.2, 0.5, "导入与验证(全链路可复现)", size=18, color=BLUE, bold=True)
add_bullets(s, 0.55, 5.15, 12.2, 1.9, [
    "•  download_data.py(下载) → build_tables.py(清洗建维) → assign_neighbourhood.py(回填社区) → 导入",
    "•  本机以 SQLite 做等价端到端验证：37,811 条全部入库，视图与查询返回正确",
    "•  MySQL 侧提供 LOAD DATA 导入脚本，正式提交时按序执行即可",
], size=16)
footer(s, 7)

# ==================================================================
# 8. 可视化 Web 应用
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "可视化 Web 应用", "08")
add_bullets(s, 0.55, 1.35, 12.2, 2.4, [
    "•  架构：Flask 后端(REST 接口) + SQLite/MySQL 数据层 + Leaflet 前端",
    "•  四类图层：单点(按分级着色 + 聚类) / 热力图 / 社区面 choropleth / 浅色·暗色双底图",
    "•  筛选面板：分级 · 月份 · 类别 · 处理结果类型 · 社区，并支持「逐月播放」动画",
    "•  明细点按视口 bbox + 筛选条件动态查询——由真实 SQL 接口实现时空查询",
], size=16)
add_rect(s, 0.55, 4.0, 12.2, 2.6, LIGHT)
add_text(s, 0.85, 4.15, 11.6, 0.5, "架构与数据流", size=15, color=BLUE, bold=True)
add_text(s, 0.85, 4.7, 11.6, 1.8,
         "浏览器(Leaflet 地图 + 筛选面板)\n"
         "        │  GET /api/crimes?bbox=…&severity=…&month=…   (返回 GeoJSON)\n"
         "        ▼\n"
         "Flask 后端(参数化 SQL) ──► 星型数据库(fact_crime + 4 维度 + 地理层级)",
         size=15, color=GRAY)
footer(s, 8)

# ==================================================================
# 9. 技术亮点与合规
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "技术亮点与合规性", "09")
add_bullets(s, 0.55, 1.4, 12.2, 4.6, [
    ("•  真实数据全链路", 0),
    ("    下载 → 清洗 → 维度建模 → 建库 → 可视化，每一步可溯源、可复现", 1),
    ("•  原生时空查询", 0),
    ("    行政区划(社区) × 时间(月份) × 案件属性(分级/类别) 组合查询；视口 bbox 实时检索", 1),
    ("•  社区热点识别", 0),
    ("    21 个社区边界多边形(GeoJSON) + 案件数 choropleth，支撑警力部署研判", 1),
    ("•  轻微犯罪分级", 0),
    ("    14 类犯罪映射为 轻微/一般/较重/严重 四级，区分轻微与严重犯罪的处罚与流程差异", 1),
    ("•  合规设计", 0),
    ("    数据源天生匿名(无姓名/身份证)，脱敏视图仅保留模糊坐标，符合个人信息保护要求", 1),
], size=16)
footer(s, 9)

# ==================================================================
# 10. 总结与后续计划
# ==================================================================
s = prs.slides.add_slide(BLANK)
title_bar(s, "总结与后续计划", "10")
add_text(s, 0.55, 1.4, 12.2, 0.5, "已完成", size=20, color=GREEN, bold=True)
add_bullets(s, 0.55, 2.0, 12.2, 2.4, [
    "•  调研并选定英国 data.police.uk 作为真实数据源(国内可达、含处罚结果、天生匿名)",
    "•  获取利兹 2024H1 共 37,811 条街道级犯罪记录(100% 带经纬度)",
    "•  按方案 A 设计星型 ER 与 7 张 3NF 关系表，编写 MySQL 建库/索引/视图脚本",
    "•  构建 Flask + Leaflet 交互地图：四图层、多维筛选、逐月播放、bbox 动态查询",
], size=16)
add_text(s, 0.55, 4.6, 12.2, 0.5, "后续计划", size=20, color=BLUE, bold=True)
add_bullets(s, 0.55, 5.2, 12.2, 1.6, [
    "•  在 MySQL 环境完成原生部署验证，完善数据导入文档",
    "•  增加热点聚类、趋势预测等分析模块，补充时间轴折线图",
    "•  完善最终报告文档(需求/ER/逻辑/索引/视图/合规)",
], size=16)
add_text(s, 0.55, 6.9, 12.2, 0.5, "谢谢观看，欢迎提问", size=18, color=DARK, bold=True, align=PP_ALIGN.CENTER)
footer(s, 10)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "中期汇报_城市犯罪数据库.pptx")
prs.save(OUT)
print("已生成:", OUT)
print("页数:", len(prs.slides.__iter__.__self__._sldIdLst))
