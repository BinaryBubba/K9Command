# ADR-002: Stack and Architecture Choices

**Date:** 2026-06-07  
**Status:** Decided

## Decisions

### Modular monolith, not microservices
Single deployable application. Module boundaries enforced by folder structure and import discipline, not by network boundaries. Revisit post-MVP if scale demands it.

### Keep React + FastAPI (no Next.js rewrite)
The spec recommended Next.js but the existing React/FastAPI stack is functional, deployed, and well-understood. Rewriting the frontend framework would add months of work with no operational benefit for a single-org MVP.

### PostgreSQL as source of truth
All business data lives in PostgreSQL. Redis is available for caching and background jobs but is never the primary store for operational records.

### Organization-scoped data model
Every business table includes `organization_id` even though MVP serves one organization. This keeps the door open for multi-tenant use without a future schema migration.

### Alembic for all schema changes
`create_all()` on startup is disabled for schema changes. Every schema change goes through a versioned Alembic migration. The baseline was stamped at `a2a90aa7bdf0` on 2026-06-07.

### MinIO for file storage
Vaccination documents and incident attachments are stored in MinIO (S3-compatible). File contents are never stored in PostgreSQL.

### n8n is optional, not core
Essential transactional logic lives in the FastAPI application. n8n handles optional automations and integrations only.

### No customer-facing UI in MVP
All screens are staff and owner facing. Customer portal is deferred post-MVP.

### No billing, timeclock, or media recording in MVP
These features exist in the codebase archive but are not active in the MVP build.
