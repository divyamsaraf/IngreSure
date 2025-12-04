# Migration Strategy

## Overview
We use Supabase for our PostgreSQL database. Migrations are managed to ensure consistent database state across development and production environments.

## Workflow

### 1. Local Development
- Use the Supabase CLI to start a local instance:
  ```bash
  supabase start
  ```
- Apply changes to the local database.
- Generate a migration file:
  ```bash
  supabase db diff -f <migration_name>
  ```

### 2. Applying Migrations
- **Local:** Migrations are applied automatically when running `supabase start` or manually via `supabase db reset`.
- **Production:** Link the project to Supabase and push migrations:
  ```bash
  supabase link --project-ref <project-id>
  supabase db push
  ```

### 3. Manual Execution
For quick prototyping or if CLI is not used, SQL scripts in `database/schema.sql` can be executed directly in the Supabase Dashboard SQL Editor.

## Initial Setup
Run the contents of `database/schema.sql` to initialize the database tables and indexes.
