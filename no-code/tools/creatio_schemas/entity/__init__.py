"""Entity (object) schemas: EntitySchema, the flag catalog, the parents and templates of 8.2.3, the database check."""

from .catalog import COLUMN_FLAGS, OBJECT_FLAGS
from .schema import EntitySchema

__all__ = ["COLUMN_FLAGS", "EntitySchema", "OBJECT_FLAGS"]
