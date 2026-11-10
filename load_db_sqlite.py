# -*- coding: utf-8 -*-
"""
零依赖端到端验证: 把 data/db/ 下的星型模式 CSV 装入 SQLite, 建视图, 跑演示查询。
(正式提交用 MySQL, 见 sql/schema_mysql.sql; 本脚本用于本机无 MySQL 时验证全链路)
运行前提: build_tables.py 已生成 data/db/*.csv
运行: python load_db_sqlite.py
"""
import csv
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "urban_crime.db")
SRC = os.path.join(HERE, "data", "db")

DDL = """
DROP TABLE IF EXISTS fact_crime;
DROP TABLE IF EXISTS dim_outcome;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_time;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_neighbourhood;
DROP TABLE IF EXISTS dim_force;

CREATE TABLE dim_force (
  force_id   TEXT PRIMARY KEY,
  force_name TEXT NOT NULL
);
CREATE TABLE dim_neighbourhood (
  neighbourhood_id   TEXT PRIMARY KEY,
  neighbourhood_name TEXT NOT NULL,
  force_id           TEXT NOT NULL
);
CREATE TABLE dim_location (
  location_id      INTEGER PRIMARY KEY,
  street_id        INTEGER,
  street_name      TEXT,
  latitude         REAL,
  longitude        REAL,
  neighbourhood_id TEXT
);
CREATE TABLE dim_time (
  time_id   INTEGER PRIMARY KEY,
  month     TEXT,
  year      INTEGER,
  month_num INTEGER,
  quarter   INTEGER,
  season    TEXT
);
CREATE TABLE dim_category (
  category_id    INTEGER PRIMARY KEY,
  category_name  TEXT,
  category_cn    TEXT,
  severity_level TEXT
);
CREATE TABLE dim_outcome (
  outcome_id   INTEGER PRIMARY KEY,
  outcome_name TEXT,
  outcome_cn   TEXT,
  outcome_type TEXT
);
CREATE TABLE fact_crime (
  crime_id         INTEGER PRIMARY KEY,
  persistent_id    TEXT,
  time_id          INTEGER,
  category_id      INTEGER,
  location_id      INTEGER,
  outcome_id       INTEGER,
  context          TEXT,
  location_type    TEXT,
  location_subtype TEXT
);
CREATE INDEX idx_fc_time ON fact_crime(time_id);
CREATE INDEX idx_fc_cat  ON fact_crime(category_id);
CREATE INDEX idx_fc_loc  ON fact_crime(location_id);
CREATE INDEX idx_fc_out  ON fact_crime(outcome_id);
"""

VIEWS = """
CREATE VIEW v_case_overview AS
SELECT fc.crime_id, t.month, c.category_cn, c.severity_level,
       l.street_name, l.latitude, l.longitude,
       o.outcome_cn, o.outcome_type
FROM fact_crime fc
LEFT JOIN dim_time t     ON fc.time_id = t.time_id
LEFT JOIN dim_category c ON fc.category_id = c.category_id
LEFT JOIN dim_location l ON fc.location_id = l.location_id
LEFT JOIN dim_outcome o  ON fc.outcome_id = o.outcome_id;

CREATE VIEW v_monthly_stats AS
SELECT t.year, t.month, c.category_cn, c.severity_level, COUNT(*) AS cnt
FROM fact_crime fc
JOIN dim_time t     ON fc.time_id = t.time_id
JOIN dim_category c ON fc.category_id = c.category_id
GROUP BY t.year, t.month, c.category_cn, c.severity_level;

CREATE VIEW v_community_hotspot AS
SELECT n.neighbourhood_name, t.month, c.category_cn, COUNT(*) AS cnt
FROM fact_crime fc
JOIN dim_location l ON fc.location_id = l.location_id
LEFT JOIN dim_neighbourhood n ON l.neighbourhood_id = n.neighbourhood_id
JOIN dim_time t ON fc.time_id = t.time_id
JOIN dim_category c ON fc.category_id = c.category_id
GROUP BY n.neighbourhood_name, t.month, c.category_cn;
"""


def load_csv(conn, table, path, cols):
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    # 动态按列插入(忽略文件中多余列)
    colnames = [r for r in cols]
    placeholders = ",".join(["?"] * len(colnames))
    q = f"INSERT INTO {table} ({','.join(colnames)}) VALUES ({placeholders})"
    data = [tuple(r.get(c, None) for c in colnames) for r in rows]
    conn.executemany(q, data)
    return len(data)


def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.executescript(DDL)

    n = {}
    n["force"] = load_csv(conn, "dim_force", os.path.join(SRC, "dim_force.csv"),
                          ["force_id", "force_name"])
    n["nb"] = load_csv(conn, "dim_neighbourhood", os.path.join(SRC, "dim_neighbourhood.csv"),
                       ["neighbourhood_id", "neighbourhood_name", "force_id"])
    n["loc"] = load_csv(conn, "dim_location", os.path.join(SRC, "dim_location.csv"),
                        ["location_id", "street_id", "street_name", "latitude",
                         "longitude", "neighbourhood_id"])
    n["time"] = load_csv(conn, "dim_time", os.path.join(SRC, "dim_time.csv"),
                         ["time_id", "month", "year", "month_num", "quarter", "season"])
    n["cat"] = load_csv(conn, "dim_category", os.path.join(SRC, "dim_category.csv"),
                        ["category_id", "category_name", "category_cn", "severity_level"])
    n["out"] = load_csv(conn, "dim_outcome", os.path.join(SRC, "dim_outcome.csv"),
                        ["outcome_id", "outcome_name", "outcome_cn", "outcome_type"])
    n["fact"] = load_csv(conn, "fact_crime", os.path.join(SRC, "fact_crime.csv"),
                         ["crime_id", "persistent_id", "time_id", "category_id",
                          "location_id", "outcome_id", "context", "location_type",
                          "location_subtype"])
    conn.executescript(VIEWS)
    conn.commit()

    print("=== 载入行数 ===")
    for k, v in n.items():
        print(f"  {k:6s}: {v}")

    def q(sql, args=()):
        return conn.execute(sql, args).fetchall()

    print("\n=== 轻微犯罪分级分布 ===")
    for row in q("SELECT severity_level, COUNT(*) FROM dim_category c JOIN fact_crime f ON f.category_id=c.category_id GROUP BY severity_level ORDER BY 2 DESC"):
        print(f"  {row[0]}: {row[1]}")

    print("\n=== 犯罪类别 TOP10 ===")
    for row in q("SELECT c.category_cn, c.severity_level, COUNT(*) FROM fact_crime f JOIN dim_category c ON f.category_id=c.category_id GROUP BY c.category_cn ORDER BY 3 DESC LIMIT 10"):
        print(f"  {row[0]} [{row[1]}]: {row[2]}")

    print("\n=== 处理结果分布 ===")
    for row in q("SELECT o.outcome_cn, o.outcome_type, COUNT(*) FROM fact_crime f JOIN dim_outcome o ON f.outcome_id=o.outcome_id GROUP BY o.outcome_cn ORDER BY 3 DESC"):
        print(f"  {row[0]} [{row[1]}]: {row[2]}")

    print("\n=== 逐月案件数 ===")
    for row in q("SELECT month, COUNT(*) FROM fact_crime f JOIN dim_time t ON f.time_id=t.time_id GROUP BY month ORDER BY month"):
        print(f"  {row[0]}: {row[1]}")

    print("\n=== 定位精度分布 ===")
    for row in q("SELECT location_type, COUNT(*) FROM fact_crime GROUP BY location_type"):
        print(f"  {row[0] or '(空)'}: {row[1]}")

    print("\n=== 有坐标记录比例 ===")
    r = q("SELECT COUNT(*), SUM(latitude IS NOT NULL AND longitude IS NOT NULL) FROM dim_location")
    print(f"  {r[0][1]}/{r[0][0]} = {r[0][1]/max(r[0][0],1):.1%}")

    print("\n=== 案件全景视图样例(3行) ===")
    for row in q("SELECT * FROM v_case_overview LIMIT 3"):
        print("  ", row)

    conn.close()
    print("\nDB ->", DB)


if __name__ == "__main__":
    main()
