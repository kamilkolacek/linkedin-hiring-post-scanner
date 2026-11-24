#!/usr/bin/env python3
"""Load scan context: target companies (tracker + config), resume summary, search URLs.

Usage: python3 load_context.py [--config PATH]
Prints JSON to stdout. Read-only: never writes to the tracker or resume.
"""
import argparse
import glob
import json
import os
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
_PRIVATE = os.path.join(HERE, "..", "config.json")
_EXAMPLE = os.path.join(HERE, "..", "config.example.json")
# config.json is your private, git-ignored config; fall back to the example so tests and demos run.
DEFAULT_CONFIG = _PRIVATE if os.path.exists(_PRIVATE) else _EXAMPLE


def load_config(path):
    with open(path) as f:
        return json.load(f)


def tracker_companies(path):
    """Return {company: priority 0-100} from the Applications sheet (ATS Score % as priority)."""
    try:
        import openpyxl
    except ImportError:
        print("warning: openpyxl missing; skipping tracker", file=sys.stderr)
        return {}
    if not os.path.exists(path):
        print(f"warning: tracker not found at {path}", file=sys.stderr)
        return {}
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if "Applications" not in wb.sheetnames:
        return {}
    ws = wb["Applications"]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {}
    header = [str(h or "").strip().lower() for h in rows[0]]
    ci = header.index("company") if "company" in header else 1
    si = next((i for i, h in enumerate(header) if h.startswith("ats score")), None)
    out = {}
    for r in rows[1:]:
        name = (r[ci] or "").strip() if ci < len(r) and isinstance(r[ci], str) else None
        if not name:
            continue
        score = r[si] if si is not None and si < len(r) else None
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 70.0
        out[name] = max(out.get(name, 0), score)
    return out


def resume_text(workspace, pattern):
    try:
        from docx import Document
    except ImportError:
        return None, ""
    matches = sorted(glob.glob(os.path.join(workspace, pattern)), key=os.path.getmtime)
    if not matches:
        return None, ""
    path = matches[-1]
    doc = Document(path)
    return path, "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())


def search_url(keywords, company_ids):
    """LinkedIn content search, past 24h, newest first, restricted to authors at the given companies."""
    ids = ",".join(f'"{i}"' for i in company_ids)
    return (
        "https://www.linkedin.com/search/results/content/?keywords="
        + quote(keywords)
        + "&authorCompany=" + quote(f"[{ids}]")
        + "&datePosted=%22past-24h%22&sortBy=%22date_posted%22&origin=FACETED_SEARCH"
    )


def plan_searches(cfg, ranked, ids):
    """Solo searches for very large employers; everyone else packed group_size per search.

    Searches are ordered by the best priority they contain, then capped at max_searches_per_run.
    Returns (searches, names of companies left out by the cap).
    """
    solo = set(cfg.get("solo_search_companies", []))
    size = int(cfg.get("group_size", 8))
    cap = int(cfg.get("max_searches_per_run", 20))
    kw = cfg["search_template"]
    with_id = [(n, p) for n, p in ranked if n in ids]
    plans = [[(n, p)] for n, p in with_id if n in solo]
    rest = [(n, p) for n, p in with_id if n not in solo]
    plans += [rest[i:i + size] for i in range(0, len(rest), size)]
    plans.sort(key=lambda g: -max(p for _, p in g))
    out = [
        {"companies": [n for n, _ in g], "top_priority": max(p for _, p in g),
         "search_url": search_url(kw, [ids[n] for n, _ in g])}
        for g in plans[:cap]
    ]
    skipped = [n for g in plans[cap:] for n, _ in g]
    return out, skipped


def build(cfg):
    ws = cfg["workspace"]
    companies = tracker_companies(os.path.join(ws, cfg["tracker"]))
    for extra in cfg.get("extra_companies", []):
        companies[extra["name"]] = float(extra.get("priority", 70))
    for ex in cfg.get("exclude_companies", []):
        companies.pop(ex, None)
    ranked = sorted(companies.items(), key=lambda kv: -kv[1])
    rp = cfg.get("resume_path")
    resume_path, text = resume_text(ws, rp if rp and os.path.exists(rp) else cfg.get("resume_glob", "*.docx"))
    ids = cfg.get("company_ids", {})
    searches, skipped = plan_searches(cfg, ranked, ids)
    return {
        "companies": [{"name": n, "priority": p, "company_id": ids.get(n)} for n, p in ranked],
        "searches": searches,
        "missing_company_ids": [n for n, _ in ranked if n not in ids],
        "skipped_over_cap": skipped,
        "resume_path": resume_path,
        "resume_headline": text.splitlines()[1] if text.count("\n") >= 1 else "",
        "resume_chars": len(text),
        "github_url": cfg["github_url"],
        "proof_points": cfg["proof_points"],
        "repos": cfg["repos"],
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    args = ap.parse_args()
    print(json.dumps(build(load_config(args.config)), indent=2))
