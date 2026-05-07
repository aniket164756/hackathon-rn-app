#!/usr/bin/env python3
"""
custom-agent-runner.py

Runs the RN PR Review agent against a GitHub Pull Request using the
GitHub Models API and posts the structured review as a PR comment.

Required env vars:
  GITHUB_TOKEN       - Automatically provided by GitHub Actions
                       (needs pull-requests: write, contents: read)
  GITHUB_REPOSITORY  - e.g. "owner/repo" (auto-set by Actions)
  PR_NUMBER          - Pull request number (from github.event.pull_request.number)
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
MODELS_ENDPOINT = "https://models.inference.ai.azure.com"
MODEL = "gpt-4o"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

print(f"[config] repository={GITHUB_REPOSITORY} pr={PR_NUMBER} model={MODEL}")
print(f"[config] OPENAI_API_KEY present={bool(OPENAI_API_KEY)}")
print(f"[config] GITHUB_TOKEN present={bool(GITHUB_TOKEN)}")

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
    print(f"[github] GET {url} params={params}")
    response = requests.get(url, headers=HEADERS, params=params)
    print(f"[github] response status={response.status_code}")
    response.raise_for_status()
    return response.json()


def gh_post_comment(owner, repo, pr_number, body):
    print(f"[github] posting PR comment to {owner}/{repo}#{pr_number}")
    response = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers=HEADERS,
        json={"body": body},
    )
    print(f"[github] comment post status={response.status_code}")
    response.raise_for_status()


def get_pr_changed_files(owner, repo, pr_number):
    """Return non-removed source files changed in the PR."""
    print(f"[github] fetching changed files for PR #{pr_number}")
    files = gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
    filtered = [
        f for f in files
        if f["status"] != "removed"
        and any(f["filename"].endswith(ext) for ext in SOURCE_EXTENSIONS)
    ]
    print(f"[github] total files in PR={len(files)}, source files to review={len(filtered)}")
    for f in filtered:
        print(f"  - {f['filename']} ({f['status']})")
    return filtered


def get_file_content(owner, repo, path, ref):
    """Fetch file content at a specific ref via GitHub Contents API."""
    print(f"[github] fetching content: {path} @ {ref[:7]}")
    try:
        data = gh_get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            if len(content) > MAX_FILE_CHARS:
                print(f"[github] truncating {path}: {len(content)} -> {MAX_FILE_CHARS} chars")
                content = content[:MAX_FILE_CHARS] + f"\n... [truncated at {MAX_FILE_CHARS} chars]"
            print(f"[github] fetched {path}: {len(content)} chars")
            return content
    except requests.HTTPError as e:
        print(f"[github] ERROR fetching {path}: {e}")
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
    print(f"[prompt] agent_md={len(agent_md)} chars, file_structure={len(file_structure)} chars, rn_quality={len(rn_quality)} chars, eslintrc={len(eslintrc)} chars")
    if not agent_md:
        print("[prompt] WARNING: .github/agents/rn-pr-review.agent.md not found")
    if not rn_quality:
        print("[prompt] WARNING: .github/instructions/rn-code-quality.instructions.md not found")
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
    print("[main] starting RN PR Review agent")
    owner, repo = GITHUB_REPOSITORY.split("/", 1)
    print(f"[main] owner={owner} repo={repo}")

    pr = gh_get(f"/repos/{owner}/{repo}/pulls/{PR_NUMBER}")
    head_sha = pr["head"]["sha"]
    print(f"[main] PR head sha={head_sha}")

    changed_files = get_pr_changed_files(owner, repo, PR_NUMBER)

    if not changed_files:
        print("No source files changed — skipping review.")
        gh_post_comment(
            owner, repo, PR_NUMBER,
            "**RN PR Review**: No TypeScript/JavaScript source files changed. Nothing to review.",
        )
        return

    system_prompt = build_system_prompt()
    user_message = build_user_message(changed_files, owner, repo, head_sha)

    # Prefer explicit OpenAI credentials when provided; otherwise use GitHub Models.
    if OPENAI_API_KEY:
        print("[main] using OpenAI API")
        client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        print("[main] OPENAI_API_KEY not set — falling back to GitHub Models endpoint")
        client = OpenAI(base_url=MODELS_ENDPOINT, api_key=GITHUB_TOKEN)

    print(f"[main] sending request to model={MODEL}...")
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
    print(f"[main] received review: {len(review)} chars")
    gh_post_comment(owner, repo, PR_NUMBER, f"## 🤖 RN PR Review\n\n{review}")
    print("[main] review posted successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
