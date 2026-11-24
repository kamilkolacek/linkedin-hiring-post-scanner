#!/usr/bin/env python3
"""Rank collected LinkedIn hiring posts deterministically.

Usage: python3 score.py posts.json [--config PATH] [--context context.json] > ranked.json

posts.json: {"scanned_at": ISO, "searches": [...], "posts": [ {post}, ... ]}
post fields: company, author_name, author_headline, author_url, post_url,
             posted_hours_ago, text, role_title, location, relation (optional)

Score (0-100) = company priority (30) + role fit (40) + poster proximity (15)
                + freshness (5) + location (10: South Bay 10, other Bay Area 6,
                remote 3, unstated 0). Dropped: posts with a stated location
                outside the Bay Area, a negative keyword in the role title,
                a non-finance role, or older than 24h.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_PRIVATE = os.path.join(HERE, "..", "config.json")
_EXAMPLE = os.path.join(HERE, "..", "config.example.json")
# config.json is your private, git-ignored config; fall back to the example so tests and demos run.
DEFAULT_CONFIG = _PRIVATE if os.path.exists(_PRIVATE) else _EXAMPLE

RECRUITER_RE = re.compile(r"\b(recruit\w*|talent acquisition|talent partner|sourcer|sourcing|headhunt\w*|ta partner|people partner)\b", re.I)
MANAGER_RE = re.compile(r"\b(head of|director|vp|vice president|chief|cfo|controller|manager|lead|principal|senior manager)\b", re.I)
HIRING_LANG_RE = re.compile(r"\b(join my team|hiring for my team|i'?m hiring|my team is hiring|reporting to me|on my team)\b", re.I)

PROXIMITY = {"hiring_manager": 15, "recruiter": 10, "team_member": 5}


def kw_re(words):
    parts = sorted({re.escape(w.lower()) for w in words}, key=len, reverse=True)
    return re.compile(r"(?<![a-z0-9])(" + "|".join(parts) + r")(?![a-z0-9])", re.I) if parts else None


def hits(rx, text):
    return sorted({m.group(1).lower() for m in rx.finditer(text or "")}) if rx else []


def classify(post):
    rel = (post.get("relation") or "").strip().lower().replace(" ", "_")
    if rel in PROXIMITY:
        return rel
    head = post.get("author_headline", "")
    if RECRUITER_RE.search(head):
        return "recruiter"
    if HIRING_LANG_RE.search(post.get("text", "")) or MANAGER_RE.search(head):
        return "hiring_manager"
    return "team_member"


LOC_POINTS = {"south_bay": 10, "bay_area": 6, "remote": 3, "unknown": 0}


def location_tier(post, cfg):
    """south_bay > bay_area > remote; 'unknown' if no location is stated; 'outside' otherwise.

    Uses the stated location when there is one (the post body often mentions cities in passing),
    and falls back to the post text only when no location is stated.
    """
    locs = cfg.get("locations", {})
    stated = (post.get("location") or "").strip()
    where = stated or post.get("text", "")
    for tier in ("south_bay", "bay_area", "remote"):
        if hits(kw_re(locs.get(tier, [])), where):
            return tier
    return "outside" if stated else "unknown"


def works_at(post):
    """True if LinkedIn's authorCompany filter returned the post, or the headline names the company."""
    if post.get("verified_author_company"):
        return True
    comp = (post.get("company") or "").lower()
    head = (post.get("author_headline") or "").lower()
    return bool(comp) and comp in head


def score_post(post, cfg, priorities):
    title_text = f"{post.get('role_title', '')}"
    full = f"{title_text}\n{post.get('text', '')}"
    neg = kw_re(cfg.get("negative_keywords", []))
    if hits(neg, title_text):
        return None, "negative keyword in role title"
    hrs = post.get("posted_hours_ago")
    if hrs is None or float(hrs) > 24:
        return None, "older than 24h or unknown age"
    if not works_at(post):
        return None, "author not tied to target company"
    tier = location_tier(post, cfg)
    if tier == "outside":
        return None, f"outside the Bay Area ({post.get('location')})"

    rk = cfg["role_keywords"]
    core, ai, adj = (hits(kw_re(rk[k]), full) for k in ("core", "ai", "adjacent"))
    if not (core or adj or hits(kw_re(["finance", "financial", "accounting"]), title_text)):
        return None, "not a finance role"
    # Finance + AI focus: both sides matter; the combination is rewarded.
    fit = min(18, 6 * len(core)) + min(14, 5 * len(ai)) + min(4, 2 * len(adj))
    if core and ai:
        fit += 4
    fit = min(40, fit)

    pr = priorities.get(post.get("company"), 60.0)
    company_pts = round(30 * pr / 100, 1)
    relation = classify(post)
    prox = PROXIMITY[relation]
    fresh = round(5 * max(0.0, 1 - float(hrs) / 24), 1)
    loc = LOC_POINTS[location_tier(post, cfg)]

    matched = set(core + ai + adj)
    proofs = sorted(
        cfg["proof_points"],
        key=lambda p: -len(matched & set(t.lower() for t in p["tags"])),
    )
    proofs = [p for p in proofs if matched & set(t.lower() for t in p["tags"])][:2] or cfg["proof_points"][:1]
    repo_scores = [(len(matched & set(t.lower() for t in r["tags"])), r) for r in cfg["repos"]]
    best = max(repo_scores, key=lambda x: x[0])
    repo = best[1] if best[0] > 0 else next(r for r in cfg["repos"] if r["name"] == cfg["default_repo"])

    total = round(max(0.0, company_pts + fit + prox + fresh + loc), 1)
    return {
        **post,
        "relation": relation,
        "location_tier": location_tier(post, cfg),
        "score": total,
        "breakdown": {"company": company_pts, "role_fit": fit, "proximity": prox, "freshness": fresh, "location": loc},
        "matched_keywords": sorted(matched),
        "suggested_proof_points": proofs,
        "suggested_repo": {**repo, "url": f"{cfg['github_url'].rstrip('/')}/{repo['name']}"},
    }, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("posts")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--context", help="output of load_context.py (for company priorities)")
    args = ap.parse_args()
    cfg = json.load(open(args.config))
    data = json.load(open(args.posts))
    priorities = {}
    if args.context:
        priorities = {c["name"]: c["priority"] for c in json.load(open(args.context))["companies"]}

    seen, ranked, dropped = set(), [], []
    for p in data.get("posts", []):
        key = (p.get("author_name"), p.get("post_url") or p.get("text", "")[:80])
        if key in seen:
            continue
        seen.add(key)
        s, why = score_post(p, cfg, priorities)
        if s:
            ranked.append(s)
        else:
            dropped.append({"author_name": p.get("author_name"), "company": p.get("company"), "reason": why})
    ranked.sort(key=lambda x: (-x["score"], x.get("posted_hours_ago", 99)))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    out = {k: v for k, v in data.items() if k != "posts"}
    out.update({"github_url": cfg["github_url"], "posts": ranked, "dropped": dropped})
    json.dump(out, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
