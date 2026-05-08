/*
  Unlock Creatio packages matching a name prefix (PostgreSQL).

  Use when:
    - Packages got locked after an installation or deployment and need to be editable again.
    - You are preparing a set of packages for development after moving to a new environment.

  What the update does:
    - InstallType = 0   → marks the package as "custom" (not installed from marketplace)
    - IsLocked   = TRUE → allows the package to be modified in the configuration
    - IsChanged  = TRUE → marks the package as having pending changes

  Customize:
    - Replace 'Prefix%' with the actual package name prefix (e.g. 'UsrMyProject%').
    - To target a single package: change LIKE to = and remove the wildcard.

  Always run a SELECT first to verify which packages will be affected:
    SELECT "Name", "InstallType", "IsLocked", "IsChanged"
    FROM "SysPackage"
    WHERE "Name" LIKE 'Prefix%';
*/

UPDATE "SysPackage"
SET
    "InstallType" = 0,
    "IsLocked"    = TRUE,
    "IsChanged"   = TRUE
WHERE "Name" LIKE 'Prefix%'; -- replace with your package name prefix
