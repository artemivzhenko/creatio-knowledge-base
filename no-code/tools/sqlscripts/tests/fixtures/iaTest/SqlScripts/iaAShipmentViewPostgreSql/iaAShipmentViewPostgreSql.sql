create or replace view "iaVwShipment" as
select s."Id", s."iaNumber", "iaFnShipmentLabel"(s."iaNumber") as "Label" from "iaShipment" s;
