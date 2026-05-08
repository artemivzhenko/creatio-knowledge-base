/*
  Get detailed info about a specific foreign key constraint by name (PostgreSQL).

  Use when:
    - You have a constraint name from an error message (e.g. a FK violation) and need to
      identify which tables and columns are involved.
    - You want to verify that a FK is correctly referencing the expected table/column.

  Customize:
    - Replace the constraint name in the WHERE clause with the one you are investigating.

  Columns returned:
    constraint_name   - name of the FK constraint
    table_name        - table where the FK column lives
    column_name       - FK column in that table
    referenced_table  - table being referenced
    referenced_column - column in the referenced table (usually 'Id')
*/

SELECT
    con.conname                    AS constraint_name,
    con.conrelid::regclass::text   AS table_name,
    a.attname                      AS column_name,
    con.confrelid::regclass::text  AS referenced_table,
    b.attname                      AS referenced_column
FROM pg_constraint con
JOIN pg_attribute a ON a.attnum = ANY (con.conkey) AND a.attrelid = con.conrelid
JOIN pg_attribute b ON b.attnum = ANY (con.confkey) AND b.attrelid = con.confrelid
WHERE con.conname = 'FKkTEjOpmacog443A4YAfPs1FUB0'; -- replace with your constraint name
