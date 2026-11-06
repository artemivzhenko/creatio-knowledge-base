create or replace function "iaFnShipmentLabel"(num text) returns text
language sql immutable as $$ select 'SHP-' || coalesce(num, '?') $$;
