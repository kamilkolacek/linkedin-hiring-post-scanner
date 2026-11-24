# Instructions

## Requirements
- Claude Code with the Claude in Chrome extension, signed in to LinkedIn
- Python 3.9+; optional: `openpyxl` (job tracker spreadsheet) and `python-docx` (resume context)

## 1. Install
Clone this repo into your Claude Code skills folder as `linkedin-job-scan`, so the skill is invoked as `/linkedin-job-scan`:

```bash
git clone https://github.com/kamilkolacek/linkedin-hiring-post-scanner ~/.claude/skills/linkedin-job-scan
```

## 2. Configure (private)
```bash
cd ~/.claude/skills/linkedin-job-scan
cp config.example.json config.json
```
Edit `config.json`. It is listed in `.gitignore`, so it is never committed. Fill in:

| Key | What to put |
|---|---|
| `workspace` | Folder where scan results are written (a `scans/` subfolder is created) |
| `tracker` | Optional job-tracker `.xlsx` with an `Applications` sheet |
| `github_url` | Your public GitHub profile, linked in drafts |
| `proof_points` | Short, true statements about you. Drafts may only use these and your resume |
| `repos` / `default_repo` | Your public repos to cite, with tags that match role keywords |
| `extra_companies`, `company_ids` | Target companies and their LinkedIn numeric IDs |
| `locations` | Cities to accept, grouped by preference |
| `resume_path` | Optional. Local path only; the resume is never uploaded or committed |

To find a company's LinkedIn ID, open `linkedin.com/company/<slug>/` and take the most frequent `urn:li:company:<id>` in the page HTML.

## 3. Run
In Claude Code, run `/linkedin-job-scan`. Claude follows `SKILL.md` step by step. If LinkedIn shows a login wall, CAPTCHA or security check, the run stops; resolve it yourself in Chrome.

## 4. Verify
```bash
python3 tests/test_pipeline.py
```

## Keep your data private
- Never commit `config.json`, `scans/`, `posts_*.json`, or resumes. All are in `.gitignore`.
- Run `git status` before every commit and confirm only code and docs are staged.
- Scan results contain real people's names and your drafts; keep them local.
