#!/usr/bin/env python3
"""ساخت content.json (و پیش‌نمایش طرح‌ها و نسخهٔ Word متن‌ها) از پوشهٔ content/

ساختار: content/salon-03/istgah-02/   ← سالن و ایستگاه از نام پوشه خوانده می‌شود
        salon-00 = ورودی ، salon-b = بعثت زنانه

انواع فایل:
  متن   .md  (و .docx که خودکار به متن تبدیل می‌شود)
  طرح   .jpg .jpeg .png .tif .tiff .webp .pdf

سرآیند اختیاری فایل‌های .md:
---
title: عنوان
type: روایت
summary: یک جملهٔ کوتاه
---

اجرا:  python3 build.py      (نیاز: Pillow ، و pandoc برای ساخت Word)
"""
import json, os, re, glob, hashlib, shutil, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
GEN = os.path.join(ROOT, "generated")
TEXT_EXT = {".md", ".docx"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
DESIGN_EXT = IMG_EXT | {".pdf"}
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
except ImportError:  # پیش‌نمایش ساخته نمی‌شود، بقیه کار می‌کند
    Image = None


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def key(path):
    return hashlib.sha1(rel(path).encode("utf-8")).hexdigest()[:12]


def location(path):
    parts = os.path.relpath(path, CONTENT).split(os.sep)
    hall = next((d[6:] for d in parts if d.startswith("salon-")), "0")
    hall = hall.lstrip("0") or "0"
    st = next((d[7:] for d in parts if d.startswith("istgah-")), "")
    st = int(st) if st.isdigit() else None
    return hall, st


def front_matter(raw):
    meta, body = {}, raw
    m = re.match(r"^---\n(.*?)\n---\n?", raw, re.S)
    if m:
        body = raw[m.end():]
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, body


def slug(s):
    return re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", s.lower())).strip("-")


def toc(md):
    out = []
    for m in re.finditer(r"^(#{2,4})\s+(.+?)\s*$", md, re.M):
        title = re.sub(r"[*_`]", "", m.group(2))
        out.append({"level": len(m.group(1)), "title": title})
    return out


def docx_from_md(md_text, title, dest):
    if not shutil.which("pandoc"):
        return False
    tmp = dest + ".src.md"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{title}\"\ndir: rtl\nlang: fa-IR\n---\n\n{md_text}")
    try:
        subprocess.run(["pandoc", tmp, "-o", dest], check=True)
        return True
    except Exception:
        return False
    finally:
        os.remove(tmp)


def text_item(path, halls):
    hall, st = location(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        if not shutil.which("pandoc"):
            return None
        raw = subprocess.run(["pandoc", path, "-t", "gfm", "--wrap=none"], capture_output=True, text=True).stdout
    else:
        raw = open(path, encoding="utf-8").read()
    raw = raw.replace("\r\n", "\n")
    meta, body = front_matter(raw)
    h = halls.get(hall, {"stations": []})
    st_name = h["stations"][st - 1] if st and st <= len(h["stations"]) else None
    title = meta.get("title") or st_name
    if not title:
        m = re.search(r"^#\s+(.+)$", body, re.M)
        title = m.group(1).strip() if m else os.path.splitext(os.path.basename(path))[0]
    item = {
        "kind": "text", "file": rel(path), "title": title, "hall": hall, "station": st,
        "type": meta.get("type") or "متن", "summary": meta.get("summary", ""),
        "bytes": os.path.getsize(path), "toc": toc(body), "text": body.strip(),
    }
    # نسخهٔ Word برای دانلود
    if ext == ".docx":
        item["docx"] = rel(path)
    else:
        dest = os.path.join(GEN, "docx", key(path) + ".docx")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        stamp = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        stamp_file = dest + ".sha"
        fresh = os.path.exists(dest) and os.path.exists(stamp_file) and open(stamp_file).read() == stamp
        if fresh or docx_from_md(body, title, dest):
            open(stamp_file, "w").write(stamp)
            item["docx"] = rel(dest)
    return item


def design_item(path, halls):
    hall, st = location(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    ext = os.path.splitext(path)[1].lower()
    label = stem
    orient = None
    if "عمودی" in stem or "amudi" in stem.lower():
        label, orient = "طرح عمودی", "portrait"
    elif "افقی" in stem or "ofoghi" in stem.lower():
        label, orient = "طرح افقی", "landscape"
    item = {
        "kind": "design", "file": rel(path), "title": label, "name": os.path.basename(path),
        "hall": hall, "station": st, "type": "طرح", "format": ext[1:].upper().replace("JPEG", "JPG"),
        "bytes": os.path.getsize(path),
    }
    if Image and ext in IMG_EXT:
        k = key(path)
        big = os.path.join(GEN, "preview", k + ".webp")
        thumb = os.path.join(GEN, "thumb", k + ".webp")
        with Image.open(path) as im:
            w, h = im.size
            dpi = im.info.get("dpi")
            item.update({"w": w, "h": h})
            if dpi and dpi[0] and dpi[0] > 1:
                d = float(dpi[0])
                item["dpi"] = round(d)
                item["cm"] = [round(w / d * 2.54), round(h / d * 2.54)]
            if not orient:
                orient = "portrait" if h > w else "landscape"
            stamp = f"{os.path.getsize(path)}:{os.path.getmtime(path)}"
            sfile = big + ".sha"
            if not (os.path.exists(big) and os.path.exists(thumb) and os.path.exists(sfile) and open(sfile).read() == stamp):
                os.makedirs(os.path.dirname(big), exist_ok=True)
                os.makedirs(os.path.dirname(thumb), exist_ok=True)
                im.draft("RGB", (2400, 2400))
                rgb = im.convert("RGB")
                for dest, size, q in ((big, 2400, 82), (thumb, 720, 78)):
                    c = rgb.copy()
                    c.thumbnail((size, size), Image.LANCZOS)
                    c.save(dest, "WEBP", quality=q, method=6)
                open(sfile, "w").write(stamp)
        item["preview"] = rel(big)
        item["thumb"] = rel(thumb)
    item["orient"] = orient or "portrait"
    return item


def main():
    data = json.load(open(os.path.join(ROOT, "halls.json"), encoding="utf-8"))
    halls = {h["id"]: h for h in data["halls"]}
    items = []
    for p in sorted(glob.glob(os.path.join(CONTENT, "**", "*"), recursive=True)):
        if not os.path.isfile(p) or os.path.basename(p).lower() == "readme.md" or os.path.basename(p).startswith("."):
            continue
        ext = os.path.splitext(p)[1].lower()
        if ext in TEXT_EXT:
            it = text_item(p, halls)
        elif ext in DESIGN_EXT:
            it = design_item(p, halls)
        else:
            continue
        if it:
            items.append(it)
    out = {"parts": data["parts"], "halls": data["halls"], "items": items}
    with open(os.path.join(ROOT, "content.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    t = sum(1 for i in items if i["kind"] == "text")
    print(f"content.json: {t} متن، {len(items) - t} طرح")


if __name__ == "__main__":
    main()
