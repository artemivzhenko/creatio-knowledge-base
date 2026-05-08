/*
  Find all foreign keys that reference a specific table (PostgreSQL).

  Use when:
    - You need to understand the impact of deleting or changing a table's primary key.
    - You want to map all dependent tables before a schema change.
    - You are tracing data relationships in the Creatio DB for a given entity.

  Customize:
    - rf.relname = 'Case'   → change to the target table name
    - ra.attname = 'Id'     → change to the referenced column (usually 'Id')
    - rf_ns.nspname = 'public' → change if your schema differs

  Columns returned:
    referenced_schema   - schema of the target table
    referenced_table    - target table (the one being pointed to)
    referenced_column   - column in the target table (usually primary key)
    referencing_schema  - schema of the table that holds the FK
    referencing_table   - table that has the foreign key column
    referencing_column  - FK column in the referencing table
    constraint_name     - name of the FK constraint
    constraint_def      - full constraint definition
*/

SELECT
    rf_ns.nspname                 AS referenced_schema,
    rf.relname                    AS referenced_table,
    ra.attname                    AS referenced_column,
    ct_ns.nspname                 AS referencing_schema,
    ct.relname                    AS referencing_table,
    ca.attname                    AS referencing_column,
    con.conname                   AS constraint_name,
    pg_get_constraintdef(con.oid) AS constraint_def
FROM pg_constraint con
JOIN pg_class     ct     ON ct.oid      = con.conrelid
JOIN pg_namespace ct_ns  ON ct_ns.oid   = ct.relnamespace
JOIN pg_class     rf     ON rf.oid      = con.confrelid
JOIN pg_namespace rf_ns  ON rf_ns.oid   = rf.relnamespace
JOIN pg_attribute ca     ON ca.attrelid = con.conrelid
                         AND ca.attnum  = ANY (con.conkey)
JOIN pg_attribute ra     ON ra.attrelid = con.confrelid
                         AND ra.attnum  = ANY (con.confkey)
WHERE con.contype     = 'f'
  AND rf_ns.nspname   = 'public'
  AND rf.relname      = 'Case'   -- target table
  AND ra.attname      = 'Id'     -- referenced column
ORDER BY referencing_schema, referencing_table, constraint_name;
