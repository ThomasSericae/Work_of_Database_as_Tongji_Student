# -*- coding: utf-8 -*-
"""
抓取西约克郡 21 个社区边界, 存成 GeoJSON(供前端 choropleth 图层使用)。
运行: python build_geojson.py
输出: static/geojson/neighbourhoods.geojson
"""
import json
import os
import time
import urllib.request
import ssl
import socket

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "static", "geojson", "neighbourhoods.geojson")
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


def main():
    nbs = get_json(f"{BASE}/neighbourhoods")
    features = []
    for n in nbs:
        nid = n["id"]
        try:
            boundary = get_json(f"{BASE}/{nid}/boundary")
            # 顶点顺序为 [latitude, longitude], 转成 GeoJSON [lng, lat], 并闭合
            ring = [[float(p["longitude"]), float(p["latitude"])] for p in boundary]
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {"neighbourhood_id": nid, "name": n["name"]},
            })
            print(f"  {nid} ({n['name']}): {len(ring)} 点")
        except Exception as e:  # noqa: BLE001
            print(f"  {nid} 失败: {e}")

    geojson = {"type": "FeatureCollection", "features": features}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"完成: {len(features)} 个社区 -> {OUT}")


if __name__ == "__main__":
    main()
