#!/usr/bin/env python3
"""
custom-agent-runner.py

Runs the RN PR Review agent against a GitHub Pull Request using the
OpenAI API and posts the review as a native GitHub PR Review with
inline comments and a quality-gate exit code.

Required env vars:
  GITHUB_TOKEN       - Automatically provided by GitHub Actions
                       (needs pull-requests: write, contents: read)
  GITHUB_REPOSITORY  - e.g. "owner/repo" (auto-set by Actions)
  PR_NUMBER          - Pull request number (from github.event.pull_request.number)
  OPENAI_API_KEY     - OpenAI API key (add as a GitHub repo secret)

Optional env vars:
  OPENAI_MODEL       - Model to use (default: gpt-4o)
"""

import os
import sys
import re
import json
import base64
import requests
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER = int(os.environ["PR_NUMBER"])

GITHUB_API = "https://api.github.com"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print(
        "[error] OPENAI_API_KEY is not set.\n"
        "Add it as a GitHub repo secret:\n"
        "  GitHub repo → Settings → Secrets and variables → Actions → New repository secret\n"
        "  Name: OPENAI_API_KEY  Value: sk-...",
        file=sys.stderr,
    )
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Truncate individual files to avoid exceeding the model context window
MAX_FILE_CHARS = 8_000

# Only review these source file types
SOURCE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}

# ── GitHub API helpers ────────────────────────────────────────────────────────

def gh_get(path, params=None):
    url = f"{GITHUB_API}{path}"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def gh_post_comment(owner, repo, pr_number, body):
    response = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers=HEADERS,
        json={"body": body},
    )
    response.raise_for_status()


def delete_previous_bot_reviews(owner, repo, pr_number):
    """Dismiss any existing RN PR Review submitted by the Actions bot."""
    reviews = gh_get(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
        params={"per_page": 100},
    )
    for review in reviews:
        if review.get("user", {}).get("login") == "github-actions[bot]":
            requests.delete(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review['id']}",
                headers=HEADERS,
            )  # best-effort; dismissal errors are non-fatal

    # Also clean up any plain issue comments from previous runs
    comments = gh_get(
        f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
        params={"per_page": 100},
    )
    for comment in comments:
        if (
            comment.get("user", {}).get("login") == "github-actions[bot]"
            and comment.get("body", "").startswith("## RN PR Review")
        ):
            requests.delete(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/comments/{comment['id']}",
                headers=HEADERS,
            ).raise_for_status()


def get_pr_changed_files(owner, repo, pr_number):
    """Return non-removed source files changed in the PR."""
    files = gh_get(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
        params={"per_page": 100},
    )
    return [
        f for f in files
        if f["status"] != "removed"
        and any(f["filename"].endswith(ext) for ext in SOURCE_EXTENSIONS)
    ]


def get_file_content(owner, repo, path, ref):
    """Fetch file content at a specific ref via GitHub Contents API."""
    try:
        data = gh_get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + f"\n... [truncated at {MAX_FILE_CHARS} chars]"
            return content
    except requests.HTTPError:
        pass
    return None

# ── Prompt builders ───────────────────────────────────────────────────────────

def strip_frontmatter(text):
    """Remove YAML frontmatter (--- ... ---) from a markdown string."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip()
    return text


def read_local(path):
    """Read a repo-local file, returning None if not found."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def build_system_prompt():
    agent_md = read_local(".github/agents/rn-pr-review.agent.md") or ""
    file_structure = read_local(".github/instructions/file-structure.instructions.md") or ""
    rn_quality = read_local(".github/instructions/rn-code-quality.instructions.md") or ""
    eslintrc = (
        read_local(".eslintrc.js")
        or read_local(".eslintrc.json")
        or read_local("eslint.config.js")
        or ""
    )
    return "\n\n---\n\n".join(filter(bool, [
        strip_frontmatter(agent_md),
        f"## File Structure Conventions\n{strip_frontmatter(file_structure)}",
        f"## Code Quality Rules\n{strip_frontmatter(rn_quality)}",
        f"## ESLint Config\n```js\n{eslintrc}\n```" if eslintrc else "",
    ]))

# JSON schema the model must follow in CI mode:
_OUTPUT_SCHEMA = """
Output ONLY a valid JSON object — no markdown fences, no prose before or after.

Schema:
{
  "merge_recommendation": "HOLD" | "MERGE WITH FIXES" | "APPROVE",
  "rationale": "<one sentence>",
  "standard_summary": "<markdown summary of Step 1 findings>",
  "coverage_summary": "<markdown summary of Step 2 findings>",
  "logic_summary": "<markdown summary of Step 3 findings>",
  "findings": [
    {
      "file": "<repo-relative path>",
      "line_start": <int>,
      "line_end": <int>,
      "pillar": "Standard" | "Coverage" | "Logic",
      "category": "<short label>",
      "description": "<actionable description>",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }
  ]
}

Rules:
- overall_risk: HIGH if any finding is HIGH; MEDIUM if two or more MEDIUM with no HIGH; otherwise LOW.
- findings array must contain every individual issue found across all three pillars.
- line_start / line_end are 1-based line numbers in the file. Use 1 / 1 if a line cannot be determined.
"""


def build_user_message(pr, changed_files, owner, repo, head_sha):
    pr_title = pr.get("title", "")
    pr_body = pr.get("body") or "_(no description provided)_"
    lines = [
        f"**PR Title**: {pr_title}\n",
        f"**PR Description**:\n{pr_body}\n\n",
        _OUTPUT_SCHEMA,
        f"\nReview the following {len(changed_files)} changed file(s):\n",
    ]
    for f in changed_files:
        path = f["filename"]
        content = get_file_content(owner, repo, path, head_sha)
        ext = path.rsplit(".", 1)[-1] if "." in path else ""
        if content is None:
            lines.append(f"### `{path}`\n_(unreadable or binary — skip)_\n")
        else:
            lines.append(f"### `{path}`\n```{ext}\n{content}\n```\n")
    return "\n".join(lines)

# ── GitHub PR Review helpers ──────────────────────────────────────────────────

_RISK_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
_REC_LABEL  = {"HOLD": "🔴 HOLD", "MERGE WITH FIXES": "🟡 MERGE WITH FIXES", "APPROVE": "🟢 APPROVE"}


def build_review_body(data):
    """Build the GitHub PR Review summary body from parsed JSON."""
    rc = data.get("risk_counts", {})
    overall = data.get("overall_risk", "LOW")
    rec = data.get("merge_recommendation", "APPROVE")
    lines = [
        "## RN PR Review\n",
        "### Overall Risk Level\n",
        f"- 🔴 High: `{rc.get('high', 0)}`",
        f"- 🟡 Medium: `{rc.get('medium', 0)}`",
        f"- 🟢 Low: `{rc.get('low', 0)}`",
        f"- Lint Violations: `{rc.get('lint_violations', 0)}`",
        f"- Coverage Gaps: `{rc.get('coverage_gaps', 0)}`",
        f"- **Overall Risk**: {_RISK_EMOJI.get(overall, '🟢')}",
        "",
        f"### Merge Recommendation\n**{_REC_LABEL.get(rec, rec)}** — {data.get('rationale', '')}",
        "",
        "### Detailed Findings",
        "",
        "<details><summary>Step 1 — Standard</summary>\n",
        data.get("standard_summary", "_No issues found._"),
        "\n</details>",
        "",
        "<details><summary>Step 2 — Coverage</summary>\n",
        data.get("coverage_summary", "_No issues found._"),
        "\n</details>",
        "",
        "<details><summary>Step 3 — Logic</summary>\n",
        data.get("logic_summary", "_No issues found._"),
        "\n</details>",
    ]
    return "\n".join(lines)


def post_pr_review(owner, repo, pr_number, head_sha, data):
    """Submit a native GitHub PR Review with inline comments."""
    rec = data.get("merge_recommendation", "APPROVE")
    event = "REQUEST_CHANGES" if rec == "HOLD" else "COMMENT"

    inline_comments = []
    fallback_findings = []

    for finding in data.get("findings", []):
        file_path = finding.get("file", "")
        line = finding.get("line_end") or finding.get("line_start") or 1
        severity_emoji = _RISK_EMOJI.get(finding.get("severity", "LOW"), "🟢")
        pillar = finding.get("pillar", "")
        category = finding.get("category", "")
        description = finding.get("description", "")
        comment_body = f"{severity_emoji} **[{pillar} — {category}]** {description}"

        if file_path and line and line > 1:
            inline_comments.append({
                "path": file_path,
                "line": line,
                "side": "RIGHT",
                "body": comment_body,
            })
        else:
            fallback_findings.append(f"- {comment_body} _(file: `{file_path}`)_")

    review_body = build_review_body(data)
    if fallback_findings:
        review_body += "\n\n<details><summary>Additional Findings (no line info)</summary>\n\n"
        review_body += "\n".join(fallback_findings)
        review_body += "\n\n</details>"

    payload = {
        "commit_id": head_sha,
        "body": review_body,
        "event": event,
        "comments": inline_comments,
    }

    response = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
        headers=HEADERS,
        json=payload,
    )

    # Inline comment failures (e.g. line not in diff) — retry without inline comments
    if response.status_code == 422 and inline_comments:
        payload["comments"] = []
        response = requests.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            headers=HEADERS,
            json=payload,
        )

    response.raise_for_status()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    owner, repo = GITHUB_REPOSITORY.split("/", 1)

    pr = gh_get(f"/repos/{owner}/{repo}/pulls/{PR_NUMBER}")
    head_sha = pr["head"]["sha"]

    changed_files = get_pr_changed_files(owner, repo, PR_NUMBER)

    if not changed_files:
        gh_post_comment(
            owner, repo, PR_NUMBER,
            "**RN PR Review**: No TypeScript/JavaScript source files changed. Nothing to review.",
        )
        return

    system_prompt = build_system_prompt()
    user_message = build_user_message(pr, changed_files, owner, repo, head_sha)

    client = OpenAI(api_key=OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_completion_tokens=4096,
        response_format={"type": "json_object"},
    )

    raw = completion.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[error] Model did not return valid JSON: {exc}", file=sys.stderr)
        print(f"[debug] Raw response:\n{raw[:500]}", file=sys.stderr)
        sys.exit(1)

    delete_previous_bot_reviews(owner, repo, PR_NUMBER)
    post_pr_review(owner, repo, PR_NUMBER, head_sha, data)

    # Quality gate — fail the CI step if any HIGH severity findings exist
    high_count = data.get("risk_counts", {}).get("high", 0)
    if high_count > 0:
        print(
            f"[quality-gate] {high_count} HIGH severity finding(s) found. Failing the check.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
