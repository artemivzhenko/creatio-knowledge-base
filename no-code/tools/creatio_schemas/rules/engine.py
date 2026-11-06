"""The platform's own rule services, to prove deployed rules.

Object rules run on the server: BusinessRulesEngineService.Execute is what every Freedom UI page
calls. Page rules run in the browser; GetBusinessRules shows what the page receives.
"""

from __future__ import annotations

import json

from ..clio import Clio
from ..files import is_uid

STATES = ("Create", "Update", "Copy")  # set-values are skipped when an existing record loads (Update + DataLoaded)


def guess_type(value) -> str:
    return "Boolean" if isinstance(value, bool) else "Integer" if isinstance(value, int) else "Float2" if isinstance(value, float) else \
        "Lookup" if is_uid(value) else "ShortText"


class RuleEngine:
    def __init__(self, clio: Clio):
        self.clio = clio

    @staticmethod
    def attribute(name: str, value, type_name: str | None = None) -> dict:
        """A record value for execute(); the engine needs a type (a typeless null breaks it with a NullReference)."""
        return {"attributeName": name, "value": value, "dataValueTypeName": type_name or guess_type(value), "hasValue": value not in (None, "")}

    def execute(self, entity: str, attributes: list[dict], changed: list[str] | None = None, state: str = "Update") -> dict:
        """Run the object rules of `entity` for a record state; `changed` = attributes the user just changed (default: data loaded)."""
        triggers = [{"type": "ChangeAttributeValue", "name": t} for t in (changed or [])] or [{"type": "DataLoaded"}]
        return self.clio.call_service("ServiceModel/BusinessRulesEngineService.svc/Execute", {"contexts": [{
            "scopeName": entity, "scopeType": "Model", "scopeId": "PDS", "scopeState": state, "modelType": "crt.EntityDataSource",
            "attributes": attributes, "triggers": triggers}]})

    @staticmethod
    def actions(response: dict) -> list[dict]:
        return [a for block in response.get("businessRulesResponse") or [] for a in block.get("actions") or []]

    @staticmethod
    def errors(response: dict) -> list:
        return [e for block in response.get("businessRulesResponse") or [] for e in block.get("errors") or []]

    def page_rules(self, page: str) -> tuple[bool, list[dict]]:
        """(success, the rules the server hands to the page)."""
        resp = self.clio.call_service("ServiceModel/BusinessRulesManagerService.svc/GetBusinessRules", {"scopes": [{"name": page, "type": "ViewModel"}]})
        rules = [r for block in resp.get("businessRules") or [] for r in json.loads(block.get("businessRulesConfig") or "[]")]
        return bool(resp.get("success")), rules
