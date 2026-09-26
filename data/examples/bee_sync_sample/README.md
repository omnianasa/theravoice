# Sample `bee sync` export

The files under `conversations/` in this folder are **hand-authored demo
fixtures**, not real captured Bee data. They exist so `bee.mode: sync` (see
`docs/bee_integration.md`) can be exercised end-to-end without a real Bee
device or account -- useful for trying out `theravoice sync-bee` or the
dashboard's "Sync from Bee" button before connecting your own account.

They follow the **exact** file/field structure `bee sync` documents at
https://docs.bee.computer/docs/sync (`# Conversation <id>`, `- start_time:
...`, `## Transcriptions` / `### Transcription <id>` / `- Speaker: text`),
so `BeeSyncAdapter` parses them identically to a real export.

Six days of a short daily check-in are included; the first five are similar
in length/style (enough to build a personal baseline once
`baseline.minimum_observations` is reached), and the sixth is noticeably
shorter and more hesitant, to demonstrate `ChangeDetector` flagging a
deviation and the agents producing a `REQUEST_CHECK_IN` / exercise
suggestion.

To use your **own real** Bee data instead, delete/ignore this folder and
point `bee.sync_dir` at wherever you ran `bee sync --output <dir>`.
