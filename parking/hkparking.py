# -*- coding: utf-8 -*-
"""香港泊車實時數據層（DATA.GOV.HK / 運輸署）
- info  : https://api.data.gov.hk/v1/carpark-info-vacancy?data=info&lang=zh_TW   (~400KB, 每日變)
- vac   : https://api.data.gov.hk/v1/carpark-info-vacancy?data=vacancy           (~99KB,  每分鐘變)
兩者以 park_Id join。
vacancy_type 依 TD 規格 V1.6：
  A = 有實時數字（vacancy）
  B = 有位但無數字（vacancyDIS = 1）
  C = 已關閉／暫停
"""
import json
import urllib.request

BASE = "https://api.data.gov.hk/v1/carpark-info-vacancy"
UA = {"User-Agent": "hk-parking-hub/1.0 (+https://github.com/Beelam32)"}

FAC = {
    "evCharger": "EV",
    "disabilities": "傷健",
    "hourly": "時租",
    "monthly": "月租",
    "twentyFourHours": "24h",
    "unloading": "卸貨區",
    "washing": "洗車",
    "carWash": "洗車",
    "valetParking": "代客泊車",
    "carLift": "汽車升降機",
    "quickCharging": "快充",
}
PAY = {"octopus": "八達通", "contactless": "感應", "cash": "現金", "creditCard": "信用卡"}


def fetch(query, timeout=60):
    req = urllib.request.Request(BASE + query, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["results"]


def pull_info():
    return fetch("?data=info&lang=zh_TW")


def pull_vac():
    return fetch("?data=vacancy")


def _height(rec):
    hs = [h.get("height") for h in (rec.get("heightLimits") or []) if isinstance(h.get("height"), (int, float))]
    hs = [h for h in hs if h > 0]
    return min(hs) if hs else None


def _min_price(rec):
    pc = rec.get("privateCar")
    if not isinstance(pc, dict):
        return None
    ps = []
    for c in pc.get("hourlyCharges") or []:
        p = c.get("price")
        if isinstance(p, (int, float)) and p > 0:
            ps.append(p)
    return min(ps) if ps else None


def slim(rec):
    """把 info record 壓成前端用的短欄位。"""
    pc = rec.get("privateCar") if isinstance(rec.get("privateCar"), dict) else {}
    fac = [FAC.get(f, f) for f in (rec.get("facilities") or [])]
    pay = [PAY.get(p, p) for p in (rec.get("paymentMethods") or [])]
    return {
        "id": str(rec.get("park_Id") or ""),
        "n": rec.get("name") or "",
        "d": rec.get("district") or (rec.get("address") or {}).get("dcDistrict") or "",
        "a": rec.get("displayAddress") or "",
        "lat": round(float(rec.get("latitude") or 0), 5),
        "lng": round(float(rec.get("longitude") or 0), 5),
        "st": rec.get("opening_status") or "",
        "h": _height(rec),
        "p": _min_price(rec),
        "f": fac,
        "pm": pay,
        "cap": pc.get("capacity") if isinstance(pc.get("capacity"), int) else None,
        "web": (rec.get("website") or "").strip() or None,
        "tel": (rec.get("contactNo") or "").strip() or None,
    }


def merge(info, vac):
    """join info + vacancy -> (list, stats)"""
    vmap = {}
    for r in vac:
        pc = r.get("privateCar") or []
        if pc:
            vmap[str(r.get("park_Id"))] = pc[0]
    out = []
    for r in info:
        s = slim(r)
        v = vmap.get(s["id"]) or {}
        t = v.get("vacancy_type")
        s["vt"] = t
        n = v.get("vacancy")
        s["num"] = n if isinstance(n, int) else None
        s["upd"] = v.get("lastupdate") or ""
        mc = r.get("motorCycle")
        out.append(s)
    stats = {
        "total": len(out),
        "num": sum(1 for x in out if x["num"] is not None),
        "any": sum(1 for x in out if x["vt"] in ("A", "B")),
        "closed": sum(1 for x in out if x["vt"] == "C"),
        "price": sum(1 for x in out if x["p"] is not None),
        "height": sum(1 for x in out if x["h"] is not None),
    }
    return out, stats


if __name__ == "__main__":
    info = pull_info()
    vac = pull_vac()
    rows, st = merge(info, vac)
    comp = [x for x in rows if x["id"] in {r["park_Id"] for r in vac}]
    print("rows", len(rows), "stats", st)
    print("sample", json.dumps(rows[0], ensure_ascii=False))
