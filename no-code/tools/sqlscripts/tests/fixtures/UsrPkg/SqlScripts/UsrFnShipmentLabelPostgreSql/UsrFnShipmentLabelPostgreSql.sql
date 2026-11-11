create or replace function "UsrFnShipmentLabel"(num text) returns text
language sql immutable as $$ select 'SHP-' || coalesce(num, '?') $$;
