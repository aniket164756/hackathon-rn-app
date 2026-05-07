#!/usr/bin/env python3
"""
custom-agent-runner.py

Runs the RN PR Review agent against a GitHub Pull Request using the
OpenAI API and posts the structured review as a PR comment.

Required env vars:
  GITHUB_TOKEN       - Automatically provided by GitHub Actions
                       (needs pull-requests: write, contents: read)
  GITHUB_REPOSITORY  - e.g. "owner/repo" (auto-set by Actions)
  PR_NUMBER          - Pull request number (from github.event.pull_request.number)
  OPENAI_API_KEY     - OpenAI API key (add as a GitHub repo secret)
"""

import os
import sys
import base64
import requests
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER = int(os.environ["PR_NUMBER"])

GITHUB_API = "https://api.github.com"
MODEL = "gpt-4o"
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


def get_pr_changed_files(owner, repo, pr_number):
    """Return non-removed source files changed in the PR."""
    files = gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
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


def build_user_message(changed_files, owner, repo, head_sha):
    lines = [f"Review the following {len(changed_files)} changed file(s):\n"]
    for f in changed_files:
        path = f["filename"]
        content = get_file_content(owner, repo, path, head_sha)
        ext = path.rsplit(".", 1)[-1] if "." in path else ""
        if content is None:
            lines.append(f"### `{path}`\n_(unreadable or binary — skip)_\n")
        else:
            lines.append(f"### `{path}`\n```{ext}\n{content}\n```\n")
    return "\n".join(lines)

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
    user_message = build_user_message(changed_files, owner, repo, head_sha)

    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
    except Exception as exc:
        message = str(exc)
        if "models permission is required" in message.lower():
            raise RuntimeError(
                "GitHub Models request failed: token is missing `models` permission. "
                "Add `permissions: models: read` to the workflow, or set OPENAI_API_KEY "
                "to use OpenAI directly."
            ) from exc
        raise

    review = completion.choices[0].message.content
    gh_post_comment(owner, repo, PR_NUMBER, f"## 🤖 RN PR Review\n\n{review}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
