"""Freedom UI pages as package files: PageSchema edits the JSON sections of <Page>.js."""

from .schema import CONTROL_OF, PageSchema, compare_page_files

__all__ = ["CONTROL_OF", "PageSchema", "compare_page_files"]
