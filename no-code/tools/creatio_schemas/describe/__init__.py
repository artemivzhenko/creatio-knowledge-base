"""The describe layer: a package, a schema, one part of a schema - on request, never by reading the file."""

from .core import QueryError, describe_item, describe_package, describe_schema, open_item, parse_query
from .index import PackageIndex, find_schema, index_workspace, packages_of

__all__ = ["PackageIndex", "QueryError", "describe_item", "describe_package", "describe_schema", "find_schema", "index_workspace", "open_item", "packages_of", "parse_query"]
