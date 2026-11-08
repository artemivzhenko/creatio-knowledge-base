"""Creatio schemas stored as package files (the clio workspace layout), read and written byte-for-byte.

    Schema          base: Schemas/<Name>/ + Resources/<Name>.<Kind>/, diff(), save(), validate()
    ProcessSchema   business processes                      (creatio_schemas.process)
    RuleSchema      object and Freedom UI page business rules (creatio_schemas.rules)
    EntitySchema    objects: columns, flags, captions               (creatio_schemas.entity)
    PageSchema      Freedom UI pages: fields, grids on the page body (creatio_schemas.page)
    Package, Workspace, Resources, Descriptor, rename_schema, Clio

Pure standard library. See README.md for the layout and how to add a schema type,
a process element kind or a rule action.
"""

from .clio import Clio
from .entity import EntitySchema
from .files import DATA_VALUE_TYPES, DVT_OF, new_uid
from .page import PageSchema
from .process import ProcessSchema
from .refactor import rename_schema
from .resources import Resources
from .rules import RuleEngine, RuleSchema
from .schema import WARNING, Descriptor, Schema
from .workspace import Package, Workspace

__all__ = ["Clio", "EntitySchema", "DATA_VALUE_TYPES", "DVT_OF", "Descriptor", "Package", "PageSchema", "ProcessSchema", "Resources", "RuleEngine", "RuleSchema",
           "Schema", "WARNING", "Workspace", "new_uid", "rename_schema"]
