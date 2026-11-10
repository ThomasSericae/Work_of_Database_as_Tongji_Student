# -*- coding: utf-8 -*-
"""
把 data/crimes.csv 转换成星型模式的事实表 + 维度表 CSV, 供数据库导入。
运行前提: download_data.py 已完成, data/crimes.csv 存在。
输出到 data/db/:
  dim_force.csv, dim_neighbourhood.csv, dim_category.csv,
  dim_outcome.csv, dim_time.csv, dim_location.csv, fact_crime.csv
仅依赖标准库。运行: python build_tables.py
"""
import csv
import json
import os
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "db")
CRIMES = os.path.join(DATA, "crimes.csv")

# ---- 犯罪类别 → (中文名, 轻微犯罪分级) ----
CATEGORY_MAP = {
    "anti-social-behaviour": ("扰乱公共秩序", "轻微"),
    "bicycle-theft": ("自行车盗窃", "轻微"),
    "shoplifting": ("商店行窃", "轻微"),
    "other-theft": ("其他盗窃", "轻微"),
    "public-order": ("公共秩序", "轻微"),
    "vehicle-crime": ("涉车犯罪", "一般"),
    "criminal-damage-arson": ("毁坏财物/纵火", "一般"),
    "theft-from-the-person": ("扒窃", "一般"),
    "other-crime": ("其他犯罪", "一般"),
    "drugs": ("毒品犯罪", "较重"),
    "burglary": ("入室盗窃", "较重"),
    "possession-of-weapons": ("持有武器", "较重"),
    "robbery": ("抢劫", "严重"),
    "violent-crime": ("暴力犯罪", "严重"),
}

# ---- 处理结果 → (中文名, 类型) ----
OUTCOME_MAP = {
    "Under investigation": ("调查中", "未决型"),
    "Awaiting court outcome": ("待法院判决", "未决型"),
    "Court result unavailable": ("法院结果不可用", "未决型"),
    "Unable to prosecute suspect": ("无法起诉嫌疑人", "终止型"),
    "Investigation complete; no suspect identified": ("调查结束，未锁定嫌疑人", "终止型"),
    "Formal action is not in the public interest": ("不符公共利益，不采取行动", "终止型"),
    "Suspect charged as part of another case": ("并入另案处理", "终止型"),
    "Defendant found not guilty": ("判无罪", "终止型"),
    "Status update unavailable": ("状态更新不可用", "未决型"),
    "Action to be taken by another organisation": ("转由其他机构处理", "终止型"),
    "Further investigation is not in the public interest": ("进一步调查不符合公共利益", "终止型"),
    "Further action is not in the public interest": ("进一步行动不符合公共利益", "终止型"),
    "Offender given a caution": ("给予警告", "处罚型"),
    "Offender given penalty notice": ("罚款通知", "处罚型"),
    "Offender given community sentence": ("社区判决（社区服务）", "处罚型"),
    "Local resolution": ("现场调解/当地解决", "处罚型"),
    "Offender sent to prison": ("判处监禁", "处罚型"),
    "Offender ordered to pay compensation": ("责令赔偿", "处罚型"),
    "Offender fined": ("罚款", "处罚型"),
    "Offender deprived of property": ("没收财产", "处罚型"),
}


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    if not os.path.exists(CRIMES):
        print("缺少", CRIMES, "请先运行 download_data.py", file=sys.stderr)
        sys.exit(1)

    crimes = read_csv(CRIMES)
    print("crime 记录数:", len(crimes))

    # 1. dim_force (全英警署)
    forces = read_csv(os.path.join(DATA, "forces.csv"))
    write_csv(os.path.join(OUT, "dim_force.csv"), ["force_id", "force_name"], forces)

    # 2. dim_neighbourhood (西约克郡)
    nbs = read_csv(os.path.join(DATA, "west_yorkshire_neighbourhoods.csv"))
    nb_rows = []
    for n in nbs:
        nb_rows.append({"neighbourhood_id": n["neighbourhood_id"],
                        "neighbourhood_name": n["name"],
                        "force_id": "west-yorkshire"})
    write_csv(os.path.join(OUT, "dim_neighbourhood.csv"),
              ["neighbourhood_id", "neighbourhood_name", "force_id"], nb_rows)

    # 3. dim_category (按数据中出现的类别 + 分级)
    cats = OrderedDict()
    for r in crimes:
        c = r["category"]
        if c and c not in cats:
            cn, sev = CATEGORY_MAP.get(c, ("其他", "一般"))
            cats[c] = (cn, sev)
    cat_rows = [{"category_id": i, "category_name": c, "category_cn": v[0], "severity_level": v[1]}
                for i, (c, v) in enumerate(cats.items(), 1)]
    cat2id = {r["category_name"]: r["category_id"] for r in cat_rows}
    write_csv(os.path.join(OUT, "dim_category.csv"),
              ["category_id", "category_name", "category_cn", "severity_level"], cat_rows)

    # 4. dim_outcome (按数据中出现的处理结果)
    outs = OrderedDict()
    for r in crimes:
        o = r["outcome_category"]
        if o and o not in outs:
            cn, tp = OUTCOME_MAP.get(o, ("其他处理结果", "未决型"))
            outs[o] = (cn, tp)
    out_rows = [{"outcome_id": i, "outcome_name": o, "outcome_cn": v[0], "outcome_type": v[1]}
                for i, (o, v) in enumerate(outs.items(), 1)]
    out2id = {r["outcome_name"]: r["outcome_id"] for r in out_rows}
    write_csv(os.path.join(OUT, "dim_outcome.csv"),
              ["outcome_id", "outcome_name", "outcome_cn", "outcome_type"], out_rows)

    # 5. dim_time (月份)
    months = OrderedDict()
    for r in crimes:
        m = r["month"]
        if m and m not in months:
            y, mo = m.split("-")
            mo_int = int(mo)
            q = (mo_int - 1) // 3 + 1
            season = {12: "冬", 1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
                      6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋"}[mo_int]
            months[m] = (int(y), mo_int, q, season)
    time_rows = [{"time_id": i, "month": m, "year": v[0], "month_num": v[1],
                  "quarter": v[2], "season": v[3]} for i, (m, v) in enumerate(months.items(), 1)]
    time2id = {r["month"]: r["time_id"] for r in time_rows}
    write_csv(os.path.join(OUT, "dim_time.csv"),
              ["time_id", "month", "year", "month_num", "quarter", "season"], time_rows)

    # 6. dim_location (去重 street_id → 名称/坐标)
    locs = OrderedDict()
    for r in crimes:
        sid = r["street_id"]
        if not sid:
            continue
        if sid not in locs:
            locs[sid] = {
                "street_name": r["street_name"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
            }
    loc_rows = [{"location_id": i, "street_id": sid, "street_name": v["street_name"],
                  "latitude": v["latitude"], "longitude": v["longitude"],
                  "neighbourhood_id": ""}  # 后续 assign_neighbourhood.py 回填
                for i, (sid, v) in enumerate(locs.items(), 1)]
    loc2id = {r["street_id"]: r["location_id"] for r in loc_rows}
    write_csv(os.path.join(OUT, "dim_location.csv"),
              ["location_id", "street_id", "street_name", "latitude", "longitude", "neighbourhood_id"],
              loc_rows)

    # 7. fact_crime
    fact_rows = []
    for r in crimes:
        fact_rows.append({
            "crime_id": r["id"],
            "persistent_id": r["persistent_id"],
            "time_id": time2id.get(r["month"], ""),
            "category_id": cat2id.get(r["category"], ""),
            "location_id": loc2id.get(r["street_id"], ""),
            "outcome_id": out2id.get(r["outcome_category"], ""),
            "context": r["context"],
            "location_type": r["location_type"],
            "location_subtype": r["location_subtype"],
        })
    write_csv(os.path.join(OUT, "fact_crime.csv"),
              ["crime_id", "persistent_id", "time_id", "category_id", "location_id",
               "outcome_id", "context", "location_type", "location_subtype"], fact_rows)

    summary = {
        "crimes": len(crimes),
        "categories": len(cat_rows),
        "outcomes": len(out_rows),
        "months": len(time_rows),
        "locations": len(loc_rows),
        "forces": len(forces),
        "neighbourhoods": len(nb_rows),
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("OK:", summary)
    print("输出目录:", OUT)


if __name__ == "__main__":
    main()
