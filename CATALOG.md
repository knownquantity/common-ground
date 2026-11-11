# Catalog submission preparation

This is a template, not a submitted listing. Publish only with the repository owner's authorization, accurate identity and the exact tested commit. Repository: https://github.com/knownquantity/common-ground.

Create `plugin-catalog/common-ground.yaml` in a fork of NousResearch/hermes-agent:

```yaml
name: common-ground
repo: https://github.com/knownquantity/common-ground
sha: REPLACE_WITH_FULL_40_CHARACTER_REVIEWED_COMMIT
maintainer: knownquantity
version: "0.1.0"
description: Durable collaboration records, mutual contributions and evidence-backed commitments.
tier: community
category: tools
requires_hermes: ">=0.23.1,<0.24"
readme: true
capabilities:
  provides_tools:
    - common_ground_capture
    - common_ground_update
    - common_ground_query
    - common_ground_brief
  provides_hooks: []
  provides_middleware: []
  requires_env: []
```

PR description draft:

> Common Ground turns pasted conversations into reviewed collaboration records with shared goals, mutual contributions and source-backed commitments. Records persist across chats. It distinguishes tentative ideas from agreements, preserves revision history, surfaces conflicting changes and generates handoff briefs.
>
> Uses public `ctx.register_tool`, `ctx.register_skill`, `ctx.get_config` and `plugins.plugin_storage` APIs. No core overrides, credential reads, self-updating code, added Python dependencies, telemetry or plugin-originated network calls. Original notes, previews and records are retained locally in plaintext; Hermes may send user content to its configured model provider. Applying proposals relies on explicit conversational user approval, not an independently authenticated plugin gate. No hosted service, account requirement or additional fees. No derivation from another community plugin. AI-assisted implementation; validate and review the pinned source.
>
> Validation: replace with the results from the exact pinned commit. Include live demo link and clearly disclose any remaining model testing limitations.

Checklist:

- [ ] Actual owner/major contributor authorizes publication and submission.
- [ ] Public repository with MIT license and accurate maintainer identity.
- [ ] No caches, database files, private notes, credentials or executable binaries committed.
- [ ] Re-run tests, doctor and validate at the exact commit to be pinned.
- [ ] Run a live model-driven flow, restart Hermes, query, resolve a conflict and export.
- [ ] Inspect all scan warnings and fix failures.
- [ ] Pin full SHA and matching version; review applicable current catalog rules.
- [ ] If entering the competition, verify it is still accepting submissions, then publish an actual working demo under 90 seconds, tag NousResearch and submit the requested links separately.

References: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission and https://hermes-agent.nousresearch.com/docs/developer-guide/plugins

The supplied announcement states November 11, 2026 at 5 p.m. EST. This is not a claim of current eligibility or an entry submission.
