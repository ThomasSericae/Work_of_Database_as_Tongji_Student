# 城市计算之轻微犯罪数据库（数据库应用开发个人大作业）

基于英国警方开放数据 [data.police.uk](https://data.police.uk/) 的真实犯罪记录，构建一个面向
「城市计算」时空分析的关系数据库。数据为**利兹（Leeds）市区及近郊 2024 年 1–6 月**的街道级犯罪记录，
每条记录含**经纬度、街道、月份、犯罪类别、处理结果（处罚方式）**，并上卷到「社区 → 警署」两级地理层级。

## 为什么是英国数据（而不是美国芝加哥）

| 数据源 | 是否含经纬度 | 是否含处理结果(处罚) | 国内网络直连 |
|---|---|---|---|
| 芝加哥 Crimes-2001-to-Present | ✅ | ❌（仅"是否逮捕"布尔） | ❌ 403 被墙 |
| **英国 data.police.uk** | ✅ | ✅（警告/罚款/社区判决/调解等） | ✅ 实测可达 |
| 中国城市级逐案犯罪数据 | ❌（不公开） | ❌ | — |

英国数据还**天生不含个人姓名/身份证号**，天然满足个人信息保护合规，且类别（扰乱秩序/盗窃/毁财/涉车）
与"轻微犯罪"主题高度吻合。

## 目录结构

```
SQLwork/
├─ download_data.py          # 1. 下载(网格化多边形 API, 断点续传)
├─ build_tables.py           # 2. 转换: crimes.csv → 星型模式维度/事实 CSV
├─ assign_neighbourhood.py   # 3. 回填地点→社区归属(点在多边形内判定)
├─ load_db_sqlite.py         # 4. 零依赖端到端验证(SQLite)
├─ sql/schema_mysql.sql      # 正式提交用 MySQL 建库+索引+视图
├─ docs/设计文档_方案A.md     # ER 图 + 逻辑设计 + 分级/结果字典
├─ webapp/                   # 可视化地图 Web 应用(Flask + Leaflet)
└─ data/
   ├─ forces.csv / west_yorkshire_neighbourhoods.csv   # 维度原始数据
   ├─ crimes.csv              # 下载完成的原始事实数据(生成)
   └─ db/*.csv                # 星型模式表(生成), urban_crime.db(生成)
```

## 一键运行（本机无 MySQL 也能验证）

```bash
python download_data.py          # 下载(约几万条, 视网络需数十分钟)
python build_tables.py           # 生成 data/db/*.csv
python assign_neighbourhood.py   # (可选) 回填社区归属
python load_db_sqlite.py         # 装入 SQLite 并跑演示查询
```

正式提交（课程要求 MySQL 时）：在 MySQL 8.0 执行 `sql/schema_mysql.sql` 建库建表，
再用 `LOAD DATA INFILE`（或 `mysqlimport`）把 `data/db/*.csv` 依次导入。

## 数据模型（方案 A：收敛到时空核心）

星型模型，7 张表全部可由真实数据填充：

```
fact_crime(案件记录) ──时间── dim_time(月份/年/季/季)
        │             ──类别── dim_category(类别/分级 轻微~严重)
        │             ──地点── dim_location(经纬度/街道)
        │             ──结果── dim_outcome(处罚型/终止型/未决型)
        │
        └─ dim_location → dim_neighbourhood(社区) → dim_force(警署)
```

人员 / 警员 / 证据等维度因政府隐私脱敏不公开，故不纳入（详见 `docs/设计文档_方案A.md`）。

## 可视化地图 Web 应用

`webapp/` 是一个 Flask + Leaflet 的交互式犯罪地图，直接查询上面的 SQLite 库（可切换 MySQL）：

```bash
cd webapp
python app.py          # 打开 http://127.0.0.1:5000
```

- 四类图层：单点（按分级着色 + 聚类）、热力图、社区面（choropleth）、双底图
- 左侧筛选面板：分级 / 月份 / 类别 / 处理结果类型 / 社区；支持「逐月播放」动画
- 明细点按视口 bbox 动态查询（体现数据库时空查询能力）

依赖已装入 `webapp/lib/`（flask + pymysql），零安装即可运行；MySQL 切换见 `webapp/db.py` 顶部注释。
