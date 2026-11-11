create or replace view "UsrVwShipment" as
select s."Id", s."UsrNumber", "UsrFnShipmentLabel"(s."UsrNumber") as "Label" from "UsrShipment" s;
