# -*- coding: utf-8 -*-
"""
数据访问层: 统一 SQLite / MySQL 的薄封装。
  - 默认 SQLite(零依赖, 直接读 data/urban_crime.db);
  - 切换 MySQL: 把 DB_KIND 改成 "mysql" 并填 MYSQL_CONFIG 即可(需 pip 装 pymysql)。

说明: 原本计划用 SQLAlchemy 做双库支持, 但本机是 32 位 Python 3.10,
SQLAlchemy(>=1.4.43) 依赖的 greenlet 无 32 位 Windows 预编译轮子且需 C 编译器,
无法安装; 故用 ~40 行等价薄封装替代, 对外接口 fetchall/scalar 与 SQLAlchemy 版一致。
"""
import os
import re
import sys

# 让本应用能 import 到 webapp/lib 下本地安装的第三方包
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if os.path.isdir(_LIB) and _LIB not in sys.path:
    sys.path.insert(0, _LIB)

_BASE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BASE)

# ------------------------------------------------------------------
# 配置: 切换数据库只改这里
# ------------------------------------------------------------------
DB_KIND = "sqlite"          # "sqlite" 或 "mysql"
SQLITE_PATH = os.path.join(_PROJECT_ROOT, "data", "urban_crime.db")
MYSQL_CONFIG = dict(
    host="127.0.0.1", port=3306, user="root", password="",
    database="urban_crime", charset="utf8mb4",
)

_NAMED_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def _connect():
    if DB_KIND == "mysql":
        import pymysql
        return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **MYSQL_CONFIG)
    import sqlite3
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _execute(sql, params):
    """执行查询, 返回 (list[dict])。SQL 用 :name 命名参数, 两种库通用。"""
    params = params or {}
    conn = _connect()
    try:
        cur = conn.cursor()
        if DB_KIND == "mysql":
            cur.execute(_NAMED_RE.sub(r"%(\1)s", sql), params)
            return [dict(r) for r in cur.fetchall()]
        cur.execute(sql, params)  # sqlite3 原生支持 :name
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def fetchall(sql, params=None):
    return _execute(sql, params)


def scalar(sql, params=None):
    rows = _execute(sql, params)
    return rows[0] if rows else {}
