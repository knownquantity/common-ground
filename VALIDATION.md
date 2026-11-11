# Validation — November 11, 2026

## Tested environment

- Hermes Agent v0.23.1 (2026.9.24), stable, local checkout 3b4215785882.
- Hermes Python 3.14.9, OpenAI SDK 2.54.0, macOS.
- Domain suite: system Python 3.9.6.
- Dedicated data root: workspace `work/hermes-test`. No existing conversations or main-profile configuration used. The isolated runtime needed `hermes pm repair` to download dependencies.

## Results

- **14/14 domain and schema tests passed** (`python3 -m unittest discover -s tests -v`).
- **Plugin Doctor passed**, 4 tools and 0 hooks, using the real discovery/import/registration path.
- **Catalog validation passed** with `--install-deps`: manifest, supported version range, config schema, loading, declared tools, collision checks, dependency declaration, security scan and no-core-override check. Security scan: safe. Host isolation is reported as informational, not a sandbox guarantee.
- **Real-registry smoke test passed**: all four registered handlers executed using Hermes's temporary Doctor runtime. Capture preview left records empty; apply saved; query retrieved the same record; update completed a commitment; brief export matched returned Markdown. Argument injection, replacement payload on apply, and reimport with changed extraction were rejected. The ad-hoc smoke harness uses private Doctor test machinery outside the plugin; shipped plugin runtime uses documented public APIs only.

Covered: persistence in a fresh Python process; exact reviewed proposal application; stable IDs; proposed-versus-agreed preservation; quote and offset validation; invalid date rejection; Monday/Sunday boundaries; UTC versus New York around midnight; overdue/upcoming/undated/terminal groups; side filtering; completion evidence; conflict/clarification history; stale writes; repeated imports and retried saves; two concurrent saves; deterministic briefs and contained exports, including refusal of a symlinked export directory.

- **Isolated installation passed**: copied the source into the dedicated data root, enabled it with `hermes plugins enable common-ground`, and confirmed version 0.1.0 appears enabled in a subsequent CLI process.

## Guided live walkthrough

The user configured OpenCode Go with a model and reasoning effort (exact selections not captured). User-provided live transcripts show capture preview, explicit approval, save/read-back, retrieval after restarting Hermes, discrepancy preview and save, explicit resolution, revision history and export. The assistant inspected the first pending proposal and final exported file directly. The final fictional collaboration is revision 3: prototype due November 20, original November 13 deadline retained in history, workshop hosting unconfirmed.

Two model decisions needed correction: it initially assigned Are.na a proposed hosting commitment without an actual offer, and it initially recorded the proposed deadline only as an open question/evidence update instead of a structured discrepancy. Guided correction produced the expected behavior. Workflow instructions now explicitly address both cases; a subsequent user-run session tested the revised capture instructions with the River Lab example (see below).

The exported brief was verified on disk. Repeated source references and raw JSON discrepancy formatting were corrected afterward, and the revised export was regenerated from the same saved record.

## Second capture and cross-collaboration retrieval

User-provided live transcripts from the restarted Hermes session show a second fictional collaboration, Community research discussion with River Lab. The model kept hosting and staff time out of commitments and requested approval. One detail still needed correction: it expanded “Send an outline” to “Send an outline for the discussion session”; the user corrected the action before approving. Saved collaboration 4340145f681149e982bcc3c74e6ed7ac is revision 1, with Jordan's agreed outline due November 16, 2026.

The final query for our agreed commitments due November 16–22 returned exactly two: Jordan's outline on November 16 and Alex's prototype on November 20. It showed the original source for Jordan, confirmation evidence for Alex, and distinguished Alex's old November 13 deadline as history. This validates the guided cross-collaboration retrieval scenario as reported in the live transcript; it does not establish broad unassisted extraction reliability.

## Remaining verification

This was one guided scenario, not evidence of reliable unassisted extraction across models. The revised discrepancy instructions still need a fresh uncoached live test; the revised capture instructions were exercised with River Lab. The model also misstated the goal quote's starting offset in its prose (stored evidence used the correct offset) and called an older proposal superseded without a storage-level invalidation; instructions now clarify both. No live completion/cancellation scenario or cross-model evaluation has been run.

The model must interpret the note faithfully and request review. The plugin validates structure and quote provenance, but cannot prove semantic agreement or independently authenticate user approval. This is documented in tool descriptions, the workflow skill and README.

Repository: https://github.com/knownquantity/common-ground. No catalog PR, competition submission or posted demo has been created. Current contest eligibility has not been verified. Only v0.23.1 is tested; the manifest limits compatibility to its minor release line.
