#!/usr/bin/env python3
"""ساخت content.json از پوشهٔ content/

ساختار: content/salon-03/istgah-02/  (سالن و ایستگاه از نام پوشه خوانده می‌شود)
salon-00 = ورودی ، salon-b = بعثت زنانه
هر فایل .md می‌تواند این سرآیند را داشته باشد (همه اختیاری‌اند):

---
title: عنوان محتوا
hall: 3            # اگر نباشد، از نام پوشه خوانده می‌شود
station: 2         # شمارهٔ ایستگاه در همان سالن
type: روایت        # متن تابلو | روایت | سازهٔ هرمی | جزوه | فهرست | سند | سناریو | بریف | اطلاع‌نگاشت | آزمون
summary: یک جملهٔ کوتاه دربارهٔ محتوا
---

اجرا:  python3 build.py
"""
import json, os, re, glob

ROOT = os.path.dirname(os.path.abspath(__file__))


def parse(path):
    raw = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    meta, body = {}, raw
    m = re.match(r"^---\n(.*?)\n---\n?", raw, re.S)
    if m:
        body = raw[m.end():]
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    rel = os.path.relpath(path, os.path.join(ROOT, "content")).split(os.sep)
    hall_dir = next((d[6:] for d in rel if d.startswith("salon-")), "0")
    hall = meta.get("hall") or (hall_dir.lstrip("0") or "0")
    st_dir = next((d[7:] for d in rel if d.startswith("istgah-")), "")
    title = meta.get("title")
    if not title:
        h = re.search(r"^#\s+(.+)$", body, re.M)
        title = h.group(1).strip() if h else os.path.splitext(os.path.basename(path))[0]
    st = meta.get("station", "") or st_dir.lstrip("0")
    return {
        "file": os.path.relpath(path, ROOT).replace(os.sep, "/"),
        "title": title,
        "hall": str(hall),
        "station": int(st) if st.isdigit() else None,
        "type": meta.get("type") or "سند",
        "summary": meta.get("summary", ""),
        "text": body.strip(),
    }


def main():
    halls = json.load(open(os.path.join(ROOT, "halls.json"), encoding="utf-8"))
    items = [parse(p) for p in sorted(glob.glob(os.path.join(ROOT, "content", "**", "*.md"), recursive=True))
             if os.path.basename(p).lower() != "readme.md"]
    out = {"parts": halls["parts"], "halls": halls["halls"], "items": items}
    with open(os.path.join(ROOT, "content.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"content.json: {len(items)} محتوا")


if __name__ == "__main__":
    main()
