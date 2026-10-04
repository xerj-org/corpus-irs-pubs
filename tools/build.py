#!/usr/bin/env python3
"""Build corpus-irs-pubs: fetch IRS publication HTML, split per chapter, emit text files.

Pipeline (per pub):
  1. curl the single-page HTML (serial, 1s sleep, 30s timeout, one retry)
  2. isolate <main>, strip the xmlbc table-of-contents <ul> tree
  3. segment at document boundaries: h1[role-part], h1.title (front/back matter), h2[role-chap]
  4. tiny segments (<800 chars) merge forward; parts lead their first chapter file
  5. HTML -> text (tables as '|'-joined rows, lists as '- ' lines)
  6. hard cap 150KB: re-split at h2-h4 role-* subsections, then at line boundaries
Output: repo/<slug>/<NN>-<slug-of-title>.txt with header 'IRS Pub <no> (<year>) | <title>'
"""
import html as htmllib
import os
import re
import subprocess
import sys
import time

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
WORK = "/tmp/irs-work"
RAW = os.path.join(WORK, "raw")
OUT = os.path.join(WORK, "repo")
BASE = "https://www.irs.gov/publications"
CAP = 150 * 1024          # hard cap per file
TARGET = 140 * 1024       # aim below this when re-splitting
MIN_SEGMENT = 800         # smaller segments merge into the next one

PUBS = ["p15", "p17", "p54", "p334", "p463", "p501", "p502", "p503",
        "p523", "p525", "p551", "p590a", "p590b", "p596", "p970"]


def fetch(slug):
    """Fetch one pub page politely; return local path or None."""
    dest = os.path.join(RAW, slug + ".html")
    if os.path.exists(dest) and os.path.getsize(dest) > 100000:
        return dest
    url = f"{BASE}/{slug}"
    for attempt in (1, 2):
        try:
            r = subprocess.run(
                ["curl", "-s", "-A", UA, "--max-time", "30",
                 "-o", dest, "-w", "%{http_code}", url],
                capture_output=True, text=True, timeout=60)
            code = r.stdout.strip()
            if code == "200" and os.path.getsize(dest) > 100000:
                return dest
            sys.stderr.write(f"[{slug}] attempt {attempt}: HTTP {code}\n")
        except Exception as e:
            sys.stderr.write(f"[{slug}] attempt {attempt}: {e}\n")
        if attempt == 1:
            time.sleep(1)
    return None


def strip_toc(fragment):
    """Iteratively remove innermost <ul> blocks that carry xmlbc-link (the TOC tree)."""
    prev = None
    while prev != fragment:
        prev = fragment
        def drop(m):
            blk = m.group(0)
            if "xmlbc-link" in blk and blk.count("<ul", 0) == 1 and blk.count("</ul>") == 1:
                return ""
            return blk
        fragment = re.sub(r"(?is)<ul\b[^>]*>.*?</ul>", drop, fragment)
    return fragment


def _table_spans(fragment):
    """Depth-scan outermost <table>...</table> spans (handles nesting)."""
    spans, stack = [], []
    for m in re.finditer(r"(?is)</?table\b[^>]*>", fragment):
        if m.group(0).lower().startswith("</"):
            if stack:
                start = stack.pop()
                if not stack:
                    spans.append((start, m.end()))
        else:
            stack.append(m.start())
    return spans


def _collapse(t):
    t = htmllib.unescape(t).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _table_to_text(t):
    """Table HTML -> one line per row, cells joined with ' | '."""
    t = re.sub(r"(?i)</t[dh]>", " \x02 ", t)
    t = re.sub(r"(?i)</tr>", " \x01 ", t)
    t = re.sub(r"(?i)<br\s*/?>", " ", t)
    t = re.sub(r"(?i)</(p|div|li|h[1-6]|blockquote)>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = htmllib.unescape(t).replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)  # collapse source whitespace incl. newlines
    rows = []
    for row in t.split("\x01"):
        row = row.replace("\x02", "|")
        row = re.sub(r"\s*\|\s*", " | ", row)
        row = re.sub(r"(\| )+\|", "| ", row)
        row = row.strip(" \t\r|")
        if row:
            rows.append(row)
    return "\n".join(rows)


def _flow_to_text(t):
    t = re.sub(r"(?i)</(p|div|li|h[1-6]|table|blockquote|section|article)>", "\n", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)<li\b[^>]*>", "\n- ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    lines = []
    for line in _collapse(t).split("\n"):
        line = line.strip(" \t\r")
        if line:
            lines.append(line)
    return "\n\n".join(lines)


def to_text(fragment):
    """HTML fragment -> plain text. Tables become ' | ' rows, lists '- ' lines."""
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</(script|style|noscript|svg)>", " ", fragment)
    t = strip_toc(t)
    spans = _table_spans(t)
    out, pos = [], 0
    for s, e in spans:
        flow = _flow_to_text(t[pos:s])
        if flow:
            out.append(flow)
        tbl = _table_to_text(t[s:e])
        if tbl:
            out.append(tbl)
        pos = e
    tail = _flow_to_text(t[pos:])
    if tail:
        out.append(tail)
    return "\n\n".join(x for x in out if x)


def clean(fragment):
    txt = re.sub(r"(?s)<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", htmllib.unescape(txt)).strip()


def slugify(title, maxlen=58):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "section"


def markers_of(main):
    """Ordered (pos, kind, title) segment boundaries."""
    ms = []
    for m in re.finditer(r"(?is)<h1([^>]*)>(.*?)</h1>", main):
        attrs, inner = m.groups()
        kind = "part" if "role-part" in attrs else "doc"
        ms.append((m.start(), kind, clean(inner)))
    for m in re.finditer(r"(?is)<h2[^>]*role-chap[^>]*>(.*?)</h2>", main):
        ms.append((m.start(), "chap", clean(m.group(1))))
    ms.sort()
    return ms


def split_oversized(header, text, stem, outdir, counter, files):
    """Split >CAP text at subsection markers already flattened to lines, else evenly."""
    nbytes = len(text.encode())
    if nbytes <= CAP:
        fn = f"{counter:02d}-{stem}.txt"
        write_file(outdir, fn, header, text, files)
        return
    # approximate proportional chunking at line boundaries
    n_chunks = nbytes // TARGET + 1
    lines = text.split("\n")
    per = len(lines) // n_chunks + 1
    idx = 1
    for i in range(0, len(lines), per):
        chunk = "\n".join(lines[i:i + per])
        if not chunk.strip():
            continue
        fn = f"{counter:02d}-{stem}--pt{idx}.txt"
        write_file(outdir, fn, header, chunk, files)
        idx += 1


def write_file(outdir, fn, header, text, files):
    path = os.path.join(outdir, fn)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n\n" + text.strip() + "\n")
    files.append(path)


def process(slug, raw_path, report):
    raw = open(raw_path, encoding="utf-8", errors="replace").read()
    tm = re.search(r"<title>([^<]*)</title>", raw)
    title_tag = htmllib.unescape(tm.group(1)).strip() if tm else "?"
    m = re.search(r"(?is)<main[^>]*>(.*?)</main>", raw)
    main = m.group(1) if m else raw
    main = re.sub(r"(?is)<header[^>]*>.*?</header>", " ", main)

    pm = re.match(r"Publication ([0-9A-Ba-b-]+) \(([^)]+)\)", title_tag)
    pubno, paren = (pm.group(1), pm.group(2)) if pm else (slug.upper(), "")
    header_prefix = f"IRS Pub {pubno} ({paren})"

    ms = markers_of(main)
    if not ms:
        ms = [(0, "doc", title_tag.rsplit("|", 1)[0].strip())]
    if not any(k == "chap" for _, k, _ in ms):
        # flat publication (no chapters): subdivide at role-hd1 sections
        ms = [(0, "doc", title_tag.rsplit("|", 1)[0].strip())]
        for m2 in re.finditer(r"(?is)<h[1-6][^>]*role-hd1[^>]*>(.*?)</h[1-6]>", main):
            ms.append((m2.start(), "chap", clean(m2.group(1))))
        ms.sort()
    segs = []
    starts = [p for p, _, _ in ms] + [len(main)]
    for i, (pos, kind, title) in enumerate(ms):
        seg_html = main[pos:starts[i + 1]]
        segs.append({"kind": kind, "title": title, "html": seg_html,
                     "text": to_text(seg_html)})
    # merge tiny segments forward
    merged = []
    for s in segs:
        if merged and len(merged[-1]["text"]) < MIN_SEGMENT:
            merged[-1]["text"] = merged[-1]["text"] + "\n\n" + s["text"]
            merged[-1]["title"] = s["title"]  # tiny leader re-labelled by what follows
        else:
            merged.append(dict(s))
    if len(merged) > 1 and len(merged[-1]["text"]) < 200:
        merged.pop()

    outdir = os.path.join(OUT, slug)
    os.makedirs(outdir, exist_ok=True)
    files = []
    n = 0
    for s in merged:
        n += 1
        stem = slugify(s["title"])
        header = f"{header_prefix} | {s['title']}"
        split_oversized(header, s["text"], stem, outdir, n, files)
    sizes = [os.path.getsize(f) for f in files]
    report[slug] = {"title": title_tag.split("|")[0].strip(), "paren": paren,
                    "segments": len(merged), "files": len(files),
                    "bytes": sum(sizes), "max": max(sizes) if sizes else 0,
                    "chapters": sum(1 for s in merged if s["kind"] == "chap")}
    print(f"{slug:6} {title_tag[:58]:58} chapters={report[slug]['chapters']:3} "
          f"segments={report[slug]['segments']:3} files={report[slug]['files']:3} "
          f"max={report[slug]['max']:8}B total={report[slug]['bytes']:10}B")


def main():
    os.makedirs(RAW, exist_ok=True)
    report = {}
    for slug in PUBS:
        path = fetch(slug)
        if not path:
            report[slug] = None
            print(f"{slug:6} FETCH FAILED (404 or error) - SKIPPED")
            continue
        process(slug, path, report)
        time.sleep(1)
    import json
    with open(os.path.join(WORK, "report.json"), "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
