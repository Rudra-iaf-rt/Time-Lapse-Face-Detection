-- PostgreSQL init for Multi-Camera Re-ID
-- Runs once on first container start via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Application role notes:
-- Tables are primarily created by SQLAlchemy/Alembic at API startup.
-- This script ensures the database exists with useful extensions only.

GRANT ALL PRIVILEGES ON DATABASE multicam_reid TO postgres;
