/*
  List all user-defined triggers on a specific table (PostgreSQL).

  Use when:
    - Debugging unexpected side effects on INSERT / UPDATE / DELETE operations.
    - Auditing which functions fire on a given table.
    - Documenting schema triggers before a migration.

  Customize:
    - c.relname = 'Case'        → change to the table you want to inspect
    - n.nspname = 'public'      → change if your schema differs (or remove to search all schemas)
    - NOT t.tgisinternal        → remove this filter to include system-managed triggers

  Columns returned:
    schema_name        - schema containing the table
    table_name         - table where the trigger is defined
    trigger_name       - name of the trigger
    function_name      - PL/pgSQL function executed by the trigger
    trigger_definition - full SQL definition (via pg_get_triggerdef)
    enabled            - 'O' = enabled, 'D' = disabled
    trigger_type       - internal bitmask for timing (BEFORE/AFTER) and event (INSERT/UPDATE/DELETE)
*/

SELECT
    n.nspname                          AS schema_name,
    c.relname                          AS table_name,
    t.tgname                           AS trigger_name,
    p.proname                          AS function_name,
    pg_get_triggerdef(t.oid, true)     AS trigger_definition,
    t.tgenabled                        AS enabled,
    t.tgtype                           AS trigger_type
FROM pg_trigger    t
JOIN pg_class     c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_proc      p ON p.oid = t.tgfoid
WHERE n.nspname      = 'public'   -- schema
  AND c.relname      = 'Case'     -- target table
  AND NOT t.tgisinternal          -- user-defined triggers only
ORDER BY trigger_name;
