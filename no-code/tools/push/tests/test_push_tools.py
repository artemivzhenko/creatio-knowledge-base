"""
Tests for the push command. Pure standard library: python tests/test_push_tools.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from creatio_schemas.push import push  # noqa: E402


class FakeClio:
    """Mock Clio for testing without an environment."""
    
    def __init__(self, env: str):
        self.env = env
        self.calls = []
    
    def execute_sql(self, sql: str) -> None:
        self.calls.append(("execute_sql", sql))
    
    def sql(self, query: str) -> list[dict]:
        self.calls.append(("sql", query))
        return []


def test_push_sequence_with_fake_clio():
    """Test the push command sequence with a fake Clio."""
    logs = []
    fake_clio = FakeClio("dev")
    
    from creatio_schemas.push import _clear_is_changed, _push_pkg, _check_compilation, _publish_if_needed
    
    result = _clear_is_changed("dev", fake_clio, dry_run=False, log=logs.append)
    assert result is True
    assert any("execute_sql" in str(c) for c in fake_clio.calls)


def test_push_dry_run():
    """Test push in dry-run mode."""
    logs = []
    
    def log_fn(msg):
        logs.append(msg)
    
    from creatio_schemas.push import _clear_is_changed
    
    result = _clear_is_changed("dev", FakeClio("dev"), dry_run=True, log=log_fn)
    assert result is True
    assert len(logs) > 0


def test_detect_script_task_in_process():
    """Test detection of ProcessSchemaScriptTask in metadata."""
    import tempfile
    import shutil
    from creatio_schemas.push import _publish_if_needed
    
    tmp = Path(tempfile.mkdtemp())
    try:
        pkg = tmp / "UsrPkg"
        pkg.mkdir()
        schemas = pkg / "Schemas"
        schemas.mkdir()
        
        process_dir = schemas / "UsrProcess"
        process_dir.mkdir()
        metadata = process_dir / "metadata.json"
        metadata.write_text('{"MetaData": {"ProcessSchemaScriptTask": []}}')
        
        logs = []
        result = _publish_if_needed(pkg, "dev", FakeClio("dev"), dry_run=True, log=logs.append)
        assert result is True
        assert any("compile-configuration" in str(l) for l in logs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_publish_without_script_task():
    """Test that publish is skipped when no script tasks exist."""
    import tempfile
    import shutil
    from creatio_schemas.push import _publish_if_needed
    
    tmp = Path(tempfile.mkdtemp())
    try:
        pkg = tmp / "UsrPkg"
        pkg.mkdir()
        schemas = pkg / "Schemas"
        schemas.mkdir()
        
        entity_dir = schemas / "UsrEntity"
        entity_dir.mkdir()
        metadata = entity_dir / "metadata.json"
        metadata.write_text('{"MetaData": {"Schema": {}}}')
        
        logs = []
        result = _publish_if_needed(pkg, "dev", FakeClio("dev"), dry_run=False, log=logs.append)
        assert result is True
        assert any("not needed" in str(l) for l in logs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
