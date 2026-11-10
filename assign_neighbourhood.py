# -*- coding: utf-8 -*-
"""
把每个地点(街道)按经纬度分配回所属社区(neighbourhood), 回填 dim_location.neighbourhood_id。
方法: 调 /{force}/{neighbourhood}/boundary 取社区多边形, 用射线法做点在多边形内判定。
运行前提: build_tables.py 已生成 data/db/dim_location.csv
运行: python assign_neighbourhood.py
"""
import csv
import json
import os
import time
import urllib.request
import ssl
import socket

HERE = os.path.dirname(os.path.abspath(__file__))
LOC_CSV = os.path.join(HERE, "data", "db", "dim_location.csv")
FORCE = "west-yorkshire"
BASE = f"https://data.police.uk/api/{FORCE}"

socket.setdefaulttimeout(30)
ctx = ssl.create_default_context()


def get_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise last


def point_in_poly(lat, lng, poly):
    """射线法判断点是否在多边形(顶点列表 [(lat,lng),...]) 内。"""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        yi, xi = poly[i]
        yj, xj = poly[j]
        if ((yi > lat) != (yj > lat)) and \
           (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def main():
    if not os.path.exists(LOC_CSV):
        print("缺少", LOC_CSV, "请先运行 build_tables.py")
        return

    with open(LOC_CSV, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # 取西约克郡全部社区 id
    nbs = get_json(f"{BASE}/neighbourhoods")
    polys = {}
    print(f"社区数: {len(nbs)}")
    for n in nbs:
        nid = n["id"]
        try:
            boundary = get_json(f"{BASE}/{nid}/boundary")
            pts = [(float(p["latitude"]), float(p["longitude"])) for p in boundary]
            polys[nid] = pts
            print(f"  {nid} ({n['name']}): {len(pts)} 顶点")
        except Exception as e:  # noqa: BLE001
            print(f"  {nid} 边界获取失败: {e}")

    # 回填
    hit = 0
    for r in rows:
        try:
            lat = float(r["latitude"])
            lng = float(r["longitude"])
        except (TypeError, ValueError):
            continue
        for nid, pts in polys.items():
            if point_in_poly(lat, lng, pts):
                r["neighbourhood_id"] = nid
                hit += 1
                break

    with open(LOC_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["location_id", "street_id", "street_name",
                                          "latitude", "longitude", "neighbourhood_id"])
        w.writeheader()
        w.writerows(rows)

    print(f"完成: 已为 {hit}/{len(rows)} 个地点回填社区归属")


if __name__ == "__main__":
    main()
