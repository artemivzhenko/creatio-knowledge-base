"""Creatio schemas stored as package files (the clio workspace layout), read and written byte-for-byte.

    Schema          base: Schemas/<Name>/ + Resources/<Name>.<Kind>/, diff(), save(), validate()
    ProcessSchema   business processes                      (creatio_schemas.process)
    RuleSchema      object and Freedom UI page business rules (creatio_schemas.rules)
    EntitySchema    objects: columns, flags, captions               (creatio_schemas.entity)
    PageSchema      Freedom UI pages: fields, grids on the page body (creatio_schemas.page)
    DcmSchema       DCM cases: stages, steps, moves, filter          (creatio_schemas.dcm)
    UserTaskSchema  user tasks: parameters and the C# half           (creatio_schemas.usertask)
    Package, Workspace, Resources, Descriptor, rename_schema, Clio

Pure standard library. See README.md for the layout and how to add a schema type,
a process element kind or a rule action.
"""

from .clio import Clio
from .dcm import DcmSchema
from .entity import EntitySchema
from .files import DATA_VALUE_TYPES, DVT_OF, new_uid
from .page import PageSchema
from .process import ProcessSchema
from .refactor import rename_schema
from .resources import Resources
from .rules import RuleEngine, RuleSchema
from .schema import WARNING, Descriptor, Schema
from .usertask import UserTaskSchema
from .workspace import Package, Workspace

__all__ = ["Clio", "DcmSchema", "EntitySchema", "DATA_VALUE_TYPES", "DVT_OF", "Descriptor", "Package", "PageSchema", "ProcessSchema", "Resources", "RuleEngine",
           "RuleSchema", "Schema", "UserTaskSchema", "WARNING", "Workspace", "new_uid", "rename_schema"]
