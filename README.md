# Common Ground

Promising conversations are easy to start and easy to drop. Common Ground gives Hermes a durable record of shared goals, mutual contributions and commitments so people can turn interest into work.

**Interest is not agreement.** A possible workshop stays proposed. An explicit prototype promise can be tracked as agreed, with its source. Saving a record does not prove an external party agreed.

## What it does

Paste a note, review a proposed collaboration, approve it, then retrieve obligations in a later chat. Changes preserve history and stable IDs. Conflicting deadlines become discrepancies for clarification. Export a deterministic Markdown handoff brief.

- `common_ground_capture`: prepare, preview or apply a new collaboration.
- `common_ground_update`: prepare, preview or apply changes, completion/cancellation and discrepancy resolutions.
- `common_ground_query`: retrieve records, evidence and history; filter obligations.
- `common_ground_brief`: return Markdown and optionally export a file.

Python standard library only. SQLite stores versioned validated records as JSON, proposals and append-only revision entries in separate tables. `BEGIN IMMEDIATE` serializes approved writes. No frontend or server is required.

## Compatibility and local installation

Tested with Hermes Agent **v0.23.1 (2026.9.24)**, checkout `3b4215785882`, Python 3.14.9 on macOS. The manifest restricts installation to `>=0.23.1,<0.24`; retest before widening that range. Domain tests also pass with the system Python 3.9.6. Use Hermes's supported runtime for installation (Hermes currently supplies its own Python).

Use a dedicated development profile/data root. These commands copy only plugin source, not user conversations or credentials. From the repository directory:

```sh
export HERMES_HOME="$(mktemp -d /tmp/common-ground-hermes.XXXXXX)"
hermes pm repair
mkdir -p "$HERMES_HOME/plugins/common-ground"
cp __init__.py domain.py schemas.py plugin.yaml "$HERMES_HOME/plugins/common-ground/"
cp -R skills "$HERMES_HOME/plugins/common-ground/"
hermes plugins enable common-ground
hermes plugins doctor "$HERMES_HOME/plugins/common-ground" --ci
hermes plugins validate "$HERMES_HOME/plugins/common-ground" --install-deps
hermes
```

The new profile needs its own model setup through Hermes before interactive extraction works. Keep the printed/selected HERMES_HOME path for later sessions. Installation into your main profile is a separate deliberate action.

Set `plugins.entries.common-ground.settings.timezone` to an IANA timezone such as `America/New_York` using Hermes settings. Default: UTC. “This week” means Monday–Sunday; query results include the resolved range and timezone. Explicit `date_from`/`date_to` are inclusive. Outstanding overdue agreed items remain visible separately even outside the requested upcoming range; proposed, undated and terminal items also have separate buckets. Side, owner and status filters apply to all buckets. Search matches name, counterpart or shared goal.

## Example prompts

- “Track this collaboration with Are.na from this fictional note: …”
- “What do I owe people this week?”
- “What are we waiting on from our collaborators?”
- “Show the source for that deadline.”
- “Update this collaboration from these meeting notes.”
- “Mark the prototype as delivered.”
- “Give me a brief I can hand to our technical lead.”

Load the bundled `common-ground:workflow` skill. Tool descriptions also explain the review requirement for fresh chats.

## Review, evidence and updates

Prepare accepts a `proposal` and returns a stored `proposal_id`, the complete proposed record and before/after changes. It writes only to the proposal table. Preview retrieves that proposal. After the assistant obtains explicit approval, apply accepts only that ID; a different payload is rejected. Retried saves do not add history. Stale proposals fail without partial writes. Reimporting the same source for a saved counterpart cannot create another collaboration; exact preparation retries return the original proposal.

Approval is a **conversational policy**, not authenticated by this plugin. There is no fake `approved: true` security flag. Direct tool callers can invoke apply; do not present this as a host-enforced human approval gate. The inspected Hermes `ask_choice` API is intended for slash-command handlers, so it is not used from these model-facing tools.

Evidence quotes must occur exactly in a stored source. Optional offsets count Python Unicode characters. This establishes provenance, not truth or semantic entailment. Hermes's configured model interprets the note and constructs the extraction; deterministic validation cannot prove an interpretation correct. Review the preview.

Relative dates must be resolved against a known source date, or left null for clarification. Keep original date wording. Unknown owners remain null. An agreed commitment can be marked completed/cancelled using a new supplied note (including an explicit user update). Changes to agreed action/owner/side/deadline preserve the original and create an unresolved discrepancy. A later note plus a reviewed `resolve` action keeps or accepts the proposed changes. Old evidence and revisions remain available.

## Storage and privacy

Uses Hermes `plugins.plugin_storage.plugin_db("common-ground")` and `plugin_data_dir("common-ground")` per call. Data lives under the active profile's `plugin-data/common-ground/data.db`, outside the plugin installation tree. Exports go under `plugin-data/common-ground/exports/` with generated filenames. Arbitrary output paths are not accepted. Back up the profile's data directory, including SQLite WAL state or using SQLite backup tooling when live.

Records and previews contain the original notes in plaintext. Storage is **not encrypted**. Content passed to Hermes may be processed by its configured model provider. This plugin makes no additional third-party network calls and has no telemetry. Pending and applied proposals remain stored for audit/retry purposes; there is no retention or deletion UI in this MVP.

No automatic inbox/calendar access, CRM sync, enrichment, outbound messages, automatic follow-ups, reminders or opportunity scoring. This is a useful standalone collaboration tool; no applicant credentials or real partnerships are implied.

## Verification and demo

```sh
python3 -m unittest discover -s tests -v
hermes plugins doctor . --ci
hermes plugins validate . --install-deps
```

See `VALIDATION.md` for exact results and limits, `examples/DEMO.md` for the 60–85 second fictional scenario, and `CATALOG.md` for publication preparation. A guided live walkthrough passed capture, approval, restart retrieval, discrepancy resolution and export. Two extraction/workflow decisions required user correction; the workflow instructions were subsequently tightened. See the validation report for remaining limits.

License: MIT.
