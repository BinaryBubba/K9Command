# ADR-001: Dog Timeline Materialization Approach

**Date:** 2026-06-07  
**Status:** Decided  
**Decider:** Phase 0 assessment

## Decision

Use **Option A — Materialized timeline events**.

Write a `timeline_events` table record at the time each relevant action occurs. Each event stores a `source_record_type` and `source_record_id` back-reference to the originating record.

## Rationale

- Simpler to paginate and filter on mobile (single table query)
- Manual notes fit naturally as first-class timeline records
- Consistent read performance regardless of how many source tables exist
- The dog timeline is read far more often than it is written
- The added write complexity is acceptable given the operational read pattern

## Trade-offs

- Timeline data is duplicated from source records (summaries only, not full copies)
- Mutable source records (e.g. edited incidents) require the timeline event to store a summary snapshot, not a live reference
- Corrections to source records must update or annotate the timeline event

## Schema implications

`timeline_events` table needs:
- `id`, `organization_id`, `dog_id`, `stay_id` (nullable)
- `event_type` (enum of all categories)
- `event_timestamp`
- `author_id`, `author_name`
- `summary` (short display text)
- `detail` (JSON structured payload)
- `source_record_type`, `source_record_id`
- `visibility_level` (`staff`, `owner`)
- `correction_status` (`original`, `corrected`, `correction`)
- `created_at`
