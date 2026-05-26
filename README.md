# RN PR Review Assistant

An AI-powered pull request review assistant built for React Native that delivers intelligent, context-aware code review insights automatically — every time a PR is raised.

## What It Does

Every time a pull request is opened, updated, or reopened against this repository, a GitHub Actions workflow triggers automatically. It sends the PR diff, along with the project's coding standards, to an AI model. The model performs a structured four-pillar review — **Standard**, **Coverage**, **Logic**, and **Summary** — and posts the result as a comment directly on the PR.

The review covers:

- **Code standards** — file naming conventions, TypeScript rules, ESLint compliance, import ordering
- **Test coverage** — missing test files, untested branches, async error paths
- **React Native–specific logic** — FlatList misuse, `useEffect` cleanup, bridge/native call safety, type-safe navigation
- **Risk level and merge recommendation** — `APPROVE`, `MERGE WITH FIXES`, or `HOLD` with a rationale

---

## Architecture

The system is built in three layers that reference each other:

```
.github/
├── agents/
│   └── rn-pr-review.agent.md            ← Custom Copilot agent (VS Code)
├── instructions/
│   ├── file-structure.instructions.md   ← File naming & placement rules
│   └── rn-code-quality.instructions.md  ← RN, TS, styling & testing rules
├── scripts/
│   └── custom-agent-runner.py           ← Orchestration script (CI)
└── workflows/
    └── rn-pr-review.yml                 ← GitHub Actions workflow
```

### How It Flows

```
PR opened / updated
       │
       ▼
GitHub Actions (rn-pr-review.yml)
       │  sets env: GITHUB_TOKEN, OPENAI_API_KEY, PR_NUMBER
       ▼
custom-agent-runner.py
       │  1. Fetches PR changed files via GitHub API
       │  2. Loads agent.md + both instruction files → system prompt
       │  3. Attaches file contents → user message
       │  4. Calls OpenAI API (gpt-4o)
       ▼
AI Review (four-pillar structured output)
       │
       ▼
Posted as PR comment (replaces any previous bot comment)
```

---

## Setup

### 1. Add the `OPENAI_API_KEY` secret

The workflow requires an OpenAI API key to call `gpt-4o`.

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `OPENAI_API_KEY`
4. Value: your OpenAI API key (`sk-...`)

The `GITHUB_TOKEN` secret is provided automatically by GitHub Actions — no configuration needed.

### 2. Create the `prod` environment (optional but recommended)

The workflow runs in an environment named `prod`, which lets you add environment-level protection rules (e.g. require a reviewer before the AI posts).

1. Go to **Settings** → **Environments** → **New environment**
2. Name it `prod`
3. Add any required reviewers or branch restrictions as needed

If you skip this step, remove the `environment: prod` line from `.github/workflows/rn-pr-review.yml`.

### 3. Ensure workflow permissions

The workflow needs `pull-requests: write` to post comments. This is already declared in the workflow file. Verify your repository's **Actions** → **General** → **Workflow permissions** allows read and write permissions, or that the explicit `permissions` block in the workflow is respected.

---

## Triggering a Review

The workflow triggers automatically on:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
```

No manual steps are needed. Open a PR targeting any branch and the bot comment will appear within a minute or two.

To re-trigger on an existing PR without a new commit, close and reopen the PR.

---

## Review Output Format

The bot comment always contains two sections:

**1. Merge Recommendation** — `HOLD`, `MERGE WITH FIXES`, or `APPROVE` with a one-sentence rationale.

**2. Detailed Findings** — each pillar (Standard, Coverage, Logic) in a collapsible `<details>` block, with file, line range, category, description, and severity for every finding.

---

## VS Code Agent (Local Use)

The custom agent `.github/agents/rn-pr-review.agent.md` can also be invoked directly inside VS Code Copilot Chat using the `@RN PR Review` agent. It follows the same four-pillar review process and references the same instruction files, but runs interactively in your editor rather than in CI.

---

## Project Structure

```
src/
├── core-components/       # Shared UI components (IBL-*.component.tsx)
├── core-constants/        # Design tokens, palette (*.constant.ts)
├── core-navigations/      # Root navigation (*.navigation.tsx)
└── modules/
    ├── module1/           # Feature module
    │   ├── navigations/
    │   ├── screens/       # *.screen.tsx
    │   ├── styles/        # *.style.ts
    │   └── utils/         # *.utils.ts
    └── module2/
```

Naming and placement rules are enforced by `.github/instructions/file-structure.instructions.md`.

---

## Running the App Locally

> Ensure your environment is set up per the [React Native environment guide](https://reactnative.dev/docs/set-up-your-environment).

```sh
# Install dependencies
npm install

# iOS — install CocoaPods (first time or after native dep changes)
bundle install && bundle exec pod install

# Start Metro bundler
npm start

# Run on Android
npm run android

# Run on iOS
npm run ios
```

---

## Running Tests

```sh
npm test
```

Tests are co-located with source files following the convention `IBL-<Name>.test.tsx` for components and `*.test.ts` for utilities.

---

## Coding Standards

| Convention file | Covers |
|---|---|
| `.github/instructions/file-structure.instructions.md` | File naming, extensions, folder placement |
| `.github/instructions/rn-code-quality.instructions.md` | React Native patterns, TypeScript, styling, testing, error handling |

These files are the authoritative source for both the AI reviewer and human developers.
