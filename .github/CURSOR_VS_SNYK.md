# Cursor Security Review (GitHub Action) vs Snyk

This repo runs **both**. They overlap on “security” but do different jobs.

## Cursor agent (`cursor-security-review.yml`)

- **What it is:** Headless **Cursor `agent`** with an LLM prompt over a **unified diff** (`pr-diff.patch`) plus optional stats.
- **Strengths:** Reasoning about **context** in changed lines (auth flows, CORS, injection in new code, suspicious patterns that are not yet catalogued CVEs), natural-language **explanations** and remediation ideas.
- **Limits:** Not a guaranteed exhaustive rules engine; output varies by model/prompt; needs **`CURSOR_API_KEY`**; **not** a replacement for dependency/CVE databases or licensed policy engines.

## Snyk (`ci.yml`, `security-scan.yml`)

- **What it is:** **SCA** (dependencies, known vulns), **SAST** (Snyk Code), **container**, **IaC**, **AIBOM** — rule and database driven, with structured findings and severities tied to Snyk’s knowledge base.
- **Strengths:** **Repeatable** findings, CVE identifiers, fix advice for known issues, org reporting and gating.
- **Limits:** Less “whole story” reasoning across arbitrary business logic unless rules exist; needs **`SNYK_TOKEN`**.

## Practical split

| Question | Lean on |
|----------|---------|
| “Is this **dependency** known-bad / outdated?” | **Snyk** (SCA) |
| “Does this **diff** look risky for auth / injection / secrets in **our** code?” | **Cursor agent** (this workflow) |
| “Prove nothing in **first-party** code matches Snyk rules?” | **Snyk Code** (SAST) |

Use Cursor for **semantic PR review**; use Snyk for **inventory + CVE + policy** coverage.
