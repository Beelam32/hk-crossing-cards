# -*- coding: utf-8 -*-
"""產生手機前端用的精簡靜態資料 parking/data/info.json
只放「不常變」的欄位；實時車位由前端直接向 DATA.GOV.HK 抓。
用法：python parking/build.py            (寫檔)
      python parking/build.py --dry      (只印統計)
"""
import json
import math
import os
import re
import sys

import hkparking as HK

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "info.json")


def _key(name):
    return re.sub(r"[\s\-_()（）]", "", name or "").upper()


def _meters(a, b, c, d):
    R = 6371000.0
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(x)))


def dedupe(rows, radius=80):
    """同場地被政府一站通同 TD 各登記一次（AIRSIDE / 啟晴邨 …）。
    同名 + 相距 <80m 視為同一個，保留資料較豐富的一筆，車位取較大值。"""
    keep, merged = [], 0
    for r in sorted(rows, key=lambda x: -(len(json.dumps(x)))):
        hit = None
        for k in keep:
            if _key(k["n"]) == _key(r["n"]) and _meters(k["lat"], k["lng"], r["lat"], r["lng"]) < radius:
                hit = k
                break
        if hit:
            merged += 1
            if hit["h"] is None:
                hit["h"] = r["h"]
            if hit["p"] is None:
                hit["p"] = r["p"]
            if not hit["f"]:
                hit["f"] = r["f"]
            continue
        keep.append(r)
    return keep, merged


def main():
    info = HK.pull_info()
    rows = [HK.slim(r) for r in info if r.get("latitude") and r.get("longitude")]
    rows, merged = dedupe(rows)
    dists = sorted({x["d"] for x in rows if x["d"]})
    rows.sort(key=lambda x: (x["d"], x["n"]))
    payload = {
        "count": len(rows),
        "merged": merged,
        "districts": dists,
        "rows": rows,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    print("rows", len(rows), "merged", merged, "districts", len(dists), "bytes", len(body.encode()))
    if "--dry" in sys.argv:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
