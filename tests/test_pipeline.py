import json, os, subprocess, sys, tempfile
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(H, "..", "scripts")
tmp = tempfile.mkdtemp()
ctx = {"companies": [{"name": "ServiceNow", "priority": 97}, {"name": "Roblox", "priority": 94}, {"name": "Rippling", "priority": 87}]}
json.dump(ctx, open(f"{tmp}/ctx.json", "w"))
out = subprocess.run([sys.executable, f"{S}/score.py", f"{H}/fixture_posts.json", "--context", f"{tmp}/ctx.json"], capture_output=True, text=True, check=True).stdout
r = json.loads(out)
names = [p["author_name"] for p in r["posts"]]
print("ranked:", [(p["author_name"], p["score"], p["relation"], p["suggested_repo"]["name"]) for p in r["posts"]])
print("dropped:", r["dropped"])
assert names[0] == "Sample Leader", names
assert {d["author_name"] for d in r["dropped"]} == {"Sample Intern Post", "Old Post", "Offsite Role"}, r["dropped"]
tiers = {p["author_name"]: p["location_tier"] for p in r["posts"]}
assert tiers == {"Sample Leader": "remote", "Sample Recruiter": "bay_area", "Sample Teammate": "bay_area"}, tiers
rel = {p["author_name"]: p["relation"] for p in r["posts"]}
assert rel == {"Sample Leader": "hiring_manager", "Sample Recruiter": "recruiter", "Sample Teammate": "team_member"}, rel
assert all(0 <= p["score"] <= 100 for p in r["posts"])
# render: long note must fail, short note passes
for p in r["posts"]: p["draft_note"] = "x" * 300; p["draft_dm"] = "dm"
json.dump(r, open(f"{tmp}/ok.json", "w"))
assert subprocess.run([sys.executable, f"{S}/render.py", f"{tmp}/ok.json", f"{tmp}/ok.html"]).returncode == 0
r["posts"][0]["draft_note"] = "x" * 301
json.dump(r, open(f"{tmp}/bad.json", "w"))
assert subprocess.run([sys.executable, f"{S}/render.py", f"{tmp}/bad.json", f"{tmp}/bad.html"], capture_output=True).returncode == 1
html = open(f"{tmp}/ok.html").read()
assert "__DATA__" not in html and "<title>Hiring Post Radar</title>" in html
# leads pass through score.py and render
fx = json.load(open(f"{H}/fixture_posts.json")); fx["leads"] = [{"kind": "departure", "company": "Roblox", "person": "Sample CFO", "note": "Leaving."}]
json.dump(fx, open(f"{tmp}/fx_leads.json", "w"))
rl = json.loads(subprocess.run([sys.executable, f"{S}/score.py", f"{tmp}/fx_leads.json", "--context", f"{tmp}/ctx.json"], capture_output=True, text=True, check=True).stdout)
assert rl["leads"][0]["person"] == "Sample CFO", rl.get("leads")
assert 'id="leads"' in html and "Sample CFO" not in html
print("ALL TESTS PASSED")

# grouped search planning: solo big employers, groups of group_size, cap respected, nobody lost
sys.path.insert(0, S)
import load_context as lc
cfg = {"solo_search_companies": ["BigCo"], "group_size": 3, "max_searches_per_run": 3, "search_template": "finance"}
ranked = [("BigCo", 99), ("A", 98), ("B", 97), ("C", 96), ("D", 95), ("E", 94), ("F", 93), ("G", 92), ("NoId", 91)]
ids = {n: str(i) for i, (n, _) in enumerate(ranked) if n != "NoId"}
plans, skipped = lc.plan_searches(cfg, ranked, ids)
assert [p["companies"] for p in plans] == [["BigCo"], ["A", "B", "C"], ["D", "E", "F"]], plans
assert skipped == ["G"], skipped
assert "authorCompany=" in plans[1]["search_url"] and "%221%22%2C%222%22%2C%223%22" in plans[1]["search_url"]
print("GROUPING TESTS PASSED")
