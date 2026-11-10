# -*- coding: utf-8 -*-
"""
从英国警方开放数据 data.police.uk 下载"利兹(Leeds)市区及近郊"的街道级犯罪数据。
数据源: https://data.police.uk/docs/  (Crimes at street-level API)
策略:
  - 用经纬度多边形(poly=)把目标区域切成小网格, 逐格逐月抓取, 避免单次超 10000 条上限;
  - 每条请求带重试(指数退避), 结果增量写 JSONL, 断点可续;
  - 最后按 id 去重并输出 CSV 与统计摘要。
仅依赖 Python 标准库。运行: python download_data.py
"""
import csv
import json
import os
import random
import time
import urllib.request
import urllib.parse
import ssl
import socket

# ---------- 目标区域(利兹 Leeds 市区及近郊) ----------
LAT_MIN, LAT_MAX = 53.74, 53.86   # 纬度
LNG_MIN, LNG_MAX = -1.60, -1.44   # 经度
CELL = 0.04                       # 网格边长(度), 约 4.4 km
MONTHS = [f"2024-{m:02d}" for m in range(1, 7)]   # 2024-01 .. 2024-06

BASE_URL = "https://data.police.uk/api/crimes-street/all-crime"
OUT_JSONL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "leeds_crimes_2024H1.jsonl")
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "crimes.csv")
OUT_META = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "meta.json")

FIELDS = [
    "id", "persistent_id", "month", "category", "context",
    "location_type", "location_subtype",
    "latitude", "longitude", "street_id", "street_name",
    "outcome_category", "outcome_date",
]

socket.setdefaulttimeout(45)
ctx = ssl.create_default_context()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}


def http_get_json(url, tries=6):
    """带指数退避重试的 GET, 返回 JSON(list)."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 * (2 ** i) + random.uniform(0, 1)
            print(f"    [retry {i+1}/{tries}] {type(e).__name__}: {e} -> sleep {wait:.1f}s", flush=True)
            time.sleep(wait)
    raise last


def cells():
    """生成网格多边形(每个为矩形4角, 顺序: 西南->东南->东北->西北)."""
    polys = []
    lat = LAT_MIN
    while lat < LAT_MAX:
        lat2 = min(lat + CELL, LAT_MAX)
        lng = LNG_MIN
        while lng < LNG_MAX:
            lng2 = min(lng + CELL, LNG_MAX)
            poly = (f"{lat},{lng}:{lat},{lng2}:{lat2},{lng2}:{lat2},{lng}")
            polys.append(poly)
            lng = lng2
        lat = lat2
    return polys


def main():
    os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)
    polys = cells()
    total = 0
    seen_ids = set()
    month_counts = {}

    # 增量续写: 读入已存在的 id 集合, 避免重复
    if os.path.exists(OUT_JSONL):
        with open(OUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    seen_ids.add(obj["id"])
                except Exception:
                    pass
        print(f"续写模式: 已存在 {len(seen_ids)} 条记录", flush=True)

    with open(OUT_JSONL, "a", encoding="utf-8") as out:
        for month in MONTHS:
            month_counts[month] = 0
            for k, poly in enumerate(polys, 1):
                url = f"{BASE_URL}?poly={urllib.parse.quote(poly)}&date={month}"
                rows = http_get_json(url)
                added = 0
                for r in rows:
                    if r.get("id") in seen_ids:
                        continue
                    seen_ids.add(r.get("id"))
                    loc = r.get("location") or {}
                    street = loc.get("street") or {}
                    os_ = r.get("outcome_status") or {}
                    rec = {
                        "id": r.get("id"),
                        "persistent_id": r.get("persistent_id") or "",
                        "month": r.get("month"),
                        "category": r.get("category"),
                        "context": r.get("context") or "",
                        "location_type": r.get("location_type") or "",
                        "location_subtype": r.get("location_subtype") or "",
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "street_id": street.get("id"),
                        "street_name": street.get("name") or "",
                        "outcome_category": os_.get("category") or "",
                        "outcome_date": os_.get("date") or "",
                    }
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    added += 1
                total += added
                month_counts[month] += added
                print(f"  {month} cell {k}/{len(polys)}: +{added} (累计 {total})", flush=True)
                time.sleep(0.4)  # 温和限速, 避免触发限流

    # 输出 CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        with open(OUT_JSONL, "r", encoding="utf-8") as fin:
            for line in fin:
                line = line.strip()
                if line:
                    w.writerow(json.loads(line))

    meta = {
        "source": "https://data.police.uk/docs/ (crimes-street/all-crime)",
        "area": "Leeds (UK), bbox lat 53.74-53.86, lng -1.60--1.44",
        "months": MONTHS,
        "total_records": total,
        "per_month": month_counts,
    }
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("DONE total=", total, flush=True)
    print("CSV ->", OUT_CSV, flush=True)
    print("META ->", OUT_META, flush=True)


if __name__ == "__main__":
    main()
