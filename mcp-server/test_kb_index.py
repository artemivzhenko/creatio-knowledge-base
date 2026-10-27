"""
Checks for the search core. Pure standard library:  python test_kb_index.py
(also collected by pytest).
"""

from pathlib import Path

from kb_index import KnowledgeBase, default_root, tokenize

KB = KnowledgeBase(default_root())


def top(query: str, area: str | None = None) -> str:
    return KB.search(query, area=area, limit=1)[0][0].id


def test_tokenize_splits_dotted_and_camel_and_stems():
    toks = tokenize("crt.OpenLookupPageRequest pagination files")
    assert "crt.openlookuppagerequest" in toks
    assert "lookup" in toks and "page" in toks
    assert tokenize("pagination") == tokenize("paginate")
    assert tokenize("files") == tokenize("file")
    assert tokenize("Freedom UI") == []


def test_index_is_complete_and_headers_parse():
    assert len(KB.recipes) >= 169
    assert KB.recipes["Frontend/Mobile/HowToCreateMobileRequestHandlerModule"].title.startswith("How to create a Mobile SDK")
    assert not KB.skipped, KB.skipped


def test_ranking_on_known_queries():
    assert top("filter a lookup field", "ClassicUI") == "Frontend/ClassicUI/Fields/HowToFilterLookupField"
    assert top("EntitySchemaQuery pagination") == "Backend/C#/ESQ/HowToPaginateWithEntitySchemaQueryOptions"
    assert top("upload file freedom ui", "FreedomUI") == "Frontend/FreedomUI/HowToUploadAndShowFiles"
    # Area words are stopwords, so this must not surface the JS-library recipe.
    assert "Frontend/FreedomUI/HowToUploadAndShowFiles" in [r.id for r, _ in KB.search("upload file freedom ui", limit=2)]
    assert top("event listener prevent save") == "Backend/C#/HowToPreventRecordSaveWithEventListener"
    assert top("mobile request handler module") == "Frontend/Mobile/HowToCreateMobileRequestHandlerModule"
    assert top("custom angular component remote module") == "Frontend/RemoteModule/HowToCreateCustomAngularViewElement"
    # Project template folders (package.json inside) are not indexed as recipes.
    assert not [r for r in KB.recipes if "/template/" in r or "/example4/" in r]


def test_get_tolerates_ext_and_bare_name_but_not_ambiguity():
    assert KB.get("Backend/C#/HowToRunBackgroundTask.cs") is not None
    assert KB.get("HowToRunBackgroundTask") is not None
    assert KB.get("HowToFilterLookupField") is None
    assert {r.area for r in KB.same_name("HowToFilterLookupField")} == {"ClassicUI", "FreedomUI"}


def test_find_api_matches_bare_and_dotted():
    ids = [r.id for r, _ in KB.find_api("OpenLookupPageRequest")]
    assert "Frontend/FreedomUI/Navigation/HowToOpenLookupPageAndCreateLinks" in ids


def test_code_style_whole_and_section():
    if not (Path(KB.root) / "CREATIO_CODE_STYLE.md").is_file():
        return
    assert KB.code_style().startswith("# Creatio C# Code Style")
    assert KB.code_style("5").startswith("## 5. Logging")
    assert KB.code_style("review checklist").startswith("## 9.")
    assert KB.code_style("nonsense") == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
