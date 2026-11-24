# LinkedIn Hiring-Post Scanner

Repo: https://github.com/kamilkolacek/linkedin-hiring-post-scanner

A Claude Code skill that scans LinkedIn for hiring posts from the last 24 hours at your target companies, ranks them against your background, and drafts outreach notes for you to send yourself.

- **Read-only.** It never clicks Connect, Message, Follow, Like, Comment or Apply, and never sends anything.
- **Human in the loop.** You review and send every draft. See [HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md).
- **Your data stays private.** Your real settings live in `config.json`, which is git-ignored. The repo ships only `config.example.json`.

## How it works

1. `scripts/load_context.py` builds a list of target companies and LinkedIn content-search URLs (past 24h, finance hiring keywords, author-company filter).
2. Claude runs each search in your own signed-in Chrome (via the Claude in Chrome extension) and extracts posts with `scripts/extract_posts.js`.
3. `scripts/score.py` drops stale, off-location and wrong-role posts, then scores the rest out of 100 (company, role fit, poster, freshness, location).
4. Claude drafts a connection note (300 characters or fewer) and a longer message per post, using only facts you put in `proof_points` and your resume.
5. `scripts/render.py` builds an HTML results page.

## Setup

See [INSTRUCTIONS.md](INSTRUCTIONS.md). Short version:

```bash
git clone https://github.com/kamilkolacek/linkedin-hiring-post-scanner ~/.claude/skills/linkedin-job-scan
cd ~/.claude/skills/linkedin-job-scan
cp config.example.json config.json   # then edit config.json
python3 tests/test_pipeline.py
```

## Tests

```bash
python3 tests/test_pipeline.py
```

Tests run against `config.example.json` and synthetic fixtures. No personal data or network access is needed.

## License

MIT. See [LICENSE](LICENSE).
