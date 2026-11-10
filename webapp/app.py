# -*- coding: utf-8 -*-
"""
城市犯罪可视化地图 —— Flask 后端
运行: python app.py   (默认 http://127.0.0.1:5000)
前端: templates/index.html + static/js/app.js (Leaflet)
"""
import os
import sys
from collections import Counter

# 让本应用能 import 到 webapp/lib 下本地安装的第三方包(flask 等)
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if os.path.isdir(_LIB) and _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from flask import Flask, jsonify, render_template, request  # noqa: E402

import db  # noqa: E402

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # 让中文正常返回

# 所有明细/聚合查询共用的 FROM 与 JOIN(维度表齐全, 便于任意筛选)
_BASE_FROM = """
    fact_crime fc
    JOIN dim_time t       ON fc.time_id     = t.time_id
    JOIN dim_category c   ON fc.category_id = c.category_id
    LEFT JOIN dim_location l     ON fc.location_id = l.location_id
    LEFT JOIN dim_outcome o      ON fc.outcome_id  = o.outcome_id
    LEFT JOIN dim_neighbourhood n ON l.neighbourhood_id = n.neighbourhood_id
"""


def _build_filters(args):
    """根据请求参数构造 WHERE 条件(全部参数化, 不拼接用户输入)。"""
    conds, params = [], {}

    cat = args.get("category")  # 逗号分隔 category_name
    if cat:
        names = [c for c in cat.split(",") if c]
        for i, v in enumerate(names):
            params[f"c{i}"] = v
        conds.append("c.category_name IN (%s)" % ",".join(f":c{i}" for i in range(len(names))))

    sev = args.get("severity")  # 逗号分隔 severity_level
    if sev:
        levels = [s for s in sev.split(",") if s]
        for i, v in enumerate(levels):
            params[f"s{i}"] = v
        conds.append("c.severity_level IN (%s)" % ",".join(f":s{i}" for i in range(len(levels))))

    month = args.get("month")  # "2024-01"
    if month:
        conds.append("t.month = :month")
        params["month"] = month

    otype = args.get("outcome_type")
    if otype:
        conds.append("o.outcome_type = :otype")
        params["otype"] = otype

    nid = args.get("neighbourhood")
    if nid:
        conds.append("n.neighbourhood_id = :nid")
        params["nid"] = nid

    return conds, params


def _where(args):
    conds, params = _build_filters(args)
    return ("WHERE " + " AND ".join(conds)) if conds else "", params


@app.route("/")
def index():
    return render_template("index.html")


# ------------------------------------------------------------------
# 1. 总览(侧栏统计)
# ------------------------------------------------------------------
@app.route("/api/overview")
def overview():
    total = db.scalar("SELECT COUNT(*) AS c FROM fact_crime")["c"]
    severity = db.fetchall(
        "SELECT c.severity_level AS k, COUNT(*) AS v FROM fact_crime fc "
        "JOIN dim_category c ON fc.category_id = c.category_id GROUP BY c.severity_level")
    categories = db.fetchall(
        "SELECT c.category_cn AS k, c.category_name AS name, COUNT(*) AS v "
        "FROM fact_crime fc JOIN dim_category c ON fc.category_id = c.category_id "
        "GROUP BY c.category_cn, c.category_name ORDER BY v DESC")
    months = db.fetchall(
        "SELECT t.month AS k, COUNT(*) AS v FROM fact_crime fc "
        "JOIN dim_time t ON fc.time_id = t.time_id GROUP BY t.month ORDER BY t.month")
    outcome_types = db.fetchall(
        "SELECT COALESCE(o.outcome_type, '未记录') AS k, COUNT(*) AS v FROM fact_crime fc "
        "LEFT JOIN dim_outcome o ON fc.outcome_id = o.outcome_id "
        "GROUP BY COALESCE(o.outcome_type, '未记录')")
    return jsonify(total=total, severity=severity, categories=categories,
                   months=months, outcome_types=outcome_types)


# ------------------------------------------------------------------
# 2. 明细点: 按 bbox + 筛选返回 GeoJSON(FeatureCollection)
# ------------------------------------------------------------------
@app.route("/api/crimes")
def crimes():
    args = request.args
    try:
        min_lng, min_lat, max_lng, max_lat = (float(x) for x in args["bbox"].split(","))
    except (KeyError, ValueError):
        return jsonify({"error": "bbox 参数格式应为 minLng,minLat,maxLng,maxLat"}), 400

    limit = min(int(args.get("limit", 5000)), 20000)
    where, params = _where(args)
    params.update(minlat=min_lat, maxlat=max_lat, minlng=min_lng, maxlng=max_lng, limit=limit)

    sql = f"""
        SELECT fc.crime_id, fc.context, fc.location_type,
               t.month, c.category_cn, c.category_name, c.severity_level,
               l.latitude, l.longitude, l.street_name,
               o.outcome_cn, o.outcome_type
        FROM {_BASE_FROM}
        {where}
          AND l.latitude  BETWEEN :minlat AND :maxlat
          AND l.longitude BETWEEN :minlng AND :maxlng
        ORDER BY fc.crime_id
        LIMIT :limit
    """
    rows = db.fetchall(sql, params)

    features = []
    for r in rows:
        if r["latitude"] is None or r["longitude"] is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(r["longitude"]), float(r["latitude"])]},
            "properties": {
                "crime_id": r["crime_id"],
                "month": r["month"],
                "category_cn": r["category_cn"],
                "category_name": r["category_name"],
                "severity": r["severity_level"],
                "street": r["street_name"],
                "outcome_cn": r["outcome_cn"],
                "outcome_type": r["outcome_type"],
                "context": r["context"],
            },
        })
    return jsonify(type="FeatureCollection", features=features, count=len(features))


# ------------------------------------------------------------------
# 3. 热力层: 返回 [lat, lng, 权重] 网格(服务端聚合)
# ------------------------------------------------------------------
@app.route("/api/heatmap")
def heatmap():
    args = request.args
    try:
        min_lng, min_lat, max_lng, max_lat = (float(x) for x in args["bbox"].split(","))
    except (KeyError, ValueError):
        return jsonify({"error": "bbox 参数格式错误"}), 400

    where, params = _where(args)
    params.update(minlat=min_lat, maxlat=max_lat, minlng=min_lng, maxlng=max_lng)

    sql = f"""
        SELECT l.latitude, l.longitude
        FROM {_BASE_FROM}
        {where}
          AND l.latitude  BETWEEN :minlat AND :maxlat
          AND l.longitude BETWEEN :minlng AND :maxlng
    """
    rows = db.fetchall(sql, params)

    grid = Counter()
    for r in rows:
        if r["latitude"] is None or r["longitude"] is None:
            continue
        grid[(round(float(r["latitude"]), 3), round(float(r["longitude"]), 3))] += 1
    return jsonify(points=[[lat, lng, w] for (lat, lng), w in grid.items()])


# ------------------------------------------------------------------
# 4. 社区面(choropleth): 每社区案件数
# ------------------------------------------------------------------
@app.route("/api/neighbourhoods")
def neighbourhoods():
    where, params = _where(request.args)
    sql = f"""
        SELECT n.neighbourhood_id AS id, n.neighbourhood_name AS name, COUNT(*) AS count
        FROM {_BASE_FROM}
        {where}
        GROUP BY n.neighbourhood_id, n.neighbourhood_name
    """
    return jsonify(neighbourhoods=db.fetchall(sql, params))


# ------------------------------------------------------------------
# 5. 时间序列: 逐月案件数
# ------------------------------------------------------------------
@app.route("/api/time-series")
def time_series():
    where, params = _where(request.args)
    sql = f"""
        SELECT t.month AS month, COUNT(*) AS count
        FROM {_BASE_FROM}
        {where}
        GROUP BY t.month ORDER BY t.month
    """
    return jsonify(series=db.fetchall(sql, params))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
