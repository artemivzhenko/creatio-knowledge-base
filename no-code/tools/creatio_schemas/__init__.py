"""Creatio schemas stored as package files (the clio workspace layout), read and written byte-for-byte.

    Schema          base: Schemas/<Name>/ + Resources/<Name>.<Kind>/, diff(), save(), validate()
    ProcessSchema   business processes                      (creatio_schemas.process)
    RuleSchema      object and Freedom UI page business rules (creatio_schemas.rules)
    EntitySchema    objects: columns, flags, captions               (creatio_schemas.entity)
    PageSchema      Freedom UI pages: fields, grids on the page body (creatio_schemas.page)
    DcmSchema       DCM cases: stages, steps, moves, filter          (creatio_schemas.dcm)
    UserTaskSchema  user tasks: parameters and the C# half           (creatio_schemas.usertask)
    DataBinding     data bindings: rows of a table the package installs (creatio_schemas.data)
    ClassicSchema   Classic UI client schemas, read-only: sections, diff, methods (creatio_schemas.classicui)
    Package, Workspace, Resources, Descriptor, rename_schema, Clio

Pure standard library. See README.md for the layout and how to add a schema type,
a process element kind or a rule action.
"""

from .classicui import ClassicSchema
from .clio import Clio
from .data import DataBinding
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

__all__ = ["ClassicSchema", "Clio", "DataBinding", "DcmSchema", "EntitySchema", "DATA_VALUE_TYPES", "DVT_OF", "Descriptor", "Package", "PageSchema", "ProcessSchema", "Resources", "RuleEngine",
           "RuleSchema", "Schema", "UserTaskSchema", "WARNING", "Workspace", "new_uid", "rename_schema"]
