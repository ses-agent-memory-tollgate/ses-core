import os
import hashlib
import pytest
from ses.curation.fetchers import fetch_source, resolve_source_path, find_git_root
from ses.curation.normalize import normalize_markdown, slugify, NormalizedSection
from ses.curation.chunker import chunk_section, chunk_document, CurationChunk
from ses.curation.registry import SourceModel

def test_find_git_root(tmp_path):
    # Create a temp directory structure simulating a git repo
    repo_dir = tmp_path / "my_repo"
    git_dir = repo_dir / ".git"
    git_dir.mkdir(parents=True)
    
    sub_dir = repo_dir / "subdir" / "subsubdir"
    sub_dir.mkdir(parents=True)
    
    # Run find_git_root starting from sub_dir
    root = find_git_root(str(sub_dir))
    assert os.path.abspath(root) == os.path.abspath(str(repo_dir))

def test_resolve_path_local(tmp_path):
    # Relative path resolution with local_file
    base = str(tmp_path)
    res_path = resolve_source_path("docs/file.md", "local_file", base_dir=base)
    assert res_path == os.path.abspath(os.path.join(base, "docs/file.md"))
    
    # Absolute path resolution
    abs_input = os.path.abspath(os.path.join(base, "other/file.md"))
    res_path_abs = resolve_source_path(abs_input, "local_file", base_dir=base)
    assert res_path_abs == abs_input

def test_resolve_path_repo(tmp_path):
    # Simulating Git root for resolve_source_path
    repo_dir = tmp_path / "git_repo"
    (repo_dir / ".git").mkdir(parents=True)
    
    # We change the current working directory to the repo or a subdirectory of it
    orig_cwd = os.getcwd()
    try:
        os.chdir(str(repo_dir))
        res_path = resolve_source_path("src/module.py", "repo_file")
        assert res_path == os.path.abspath(os.path.join(str(repo_dir), "src/module.py"))
    finally:
        os.chdir(orig_cwd)

def test_fetch_source_local(tmp_path):
    # Create a file with CRLF line endings to test normalization
    test_file = tmp_path / "test.md"
    test_file.write_bytes(b"Hello\r\nWorld\r\n")
    
    source = SourceModel(
        source_id="test_src",
        type="local_file",
        path=str(test_file),
        title="Test Source",
        citation_base="docs/test.md"
    )
    
    fetched = fetch_source(source)
    assert fetched.source_id == "test_src"
    assert fetched.content == "Hello\nWorld\n"
    
    expected_hash = "sha256:" + hashlib.sha256(b"Hello\nWorld\n").hexdigest()
    assert fetched.source_hash == expected_hash
    assert fetched.fetched_at is not None

def test_slugify():
    assert slugify("Heading One") == "heading-one"
    assert slugify("Details - Part 1!") == "details-part-1"
    assert slugify("What's Next?") == "whats-next"
    assert slugify("  Multiple   Spaces   ") == "multiple-spaces"
    assert slugify("special_characters*&^%") == "specialcharacters"
    assert slugify("") == ""

def test_normalize_markdown_comprehensive():
    markdown_content = """This is preamble text.
It has two lines.

# Heading One
Some content here.
```python
# This is a comment inside a code block
def hello():
    pass
```
More content.

# Heading One
Duplicate heading content.

## Special & Heading!
Check special character removal.
"""
    
    sections = normalize_markdown(markdown_content, "docs/test.md")
    
    # Expected sections:
    # 1. Preamble (empty heading, empty section_id)
    # 2. Heading One (section_id: heading-one)
    # 3. Heading One (section_id: heading-one-1)
    # 4. Special & Heading! (section_id: special-heading)
    
    assert len(sections) == 4
    
    # Check preamble
    assert sections[0].heading == ""
    assert sections[0].section_id == ""
    assert sections[0].anchor == "docs/test.md"
    assert sections[0].text == "This is preamble text.\nIt has two lines."
    
    # Check first Heading One
    assert sections[1].heading == "Heading One"
    assert sections[1].section_id == "heading-one"
    assert sections[1].anchor == "docs/test.md#heading-one"
    assert "# This is a comment inside a code block" in sections[1].text
    assert "def hello():" in sections[1].text
    assert "More content." in sections[1].text
    
    # Check second Heading One (disambiguated)
    assert sections[2].heading == "Heading One"
    assert sections[2].section_id == "heading-one-1"
    assert sections[2].anchor == "docs/test.md#heading-one-1"
    assert sections[2].text == "Duplicate heading content."
    
    # Check Special & Heading!
    assert sections[3].heading == "Special & Heading!"
    assert sections[3].section_id == "special-heading"
    assert sections[3].anchor == "docs/test.md#special-heading"
    assert sections[3].text == "Check special character removal."

def test_stable_chunk_ids():
    section = NormalizedSection(
        section_id="my-section",
        heading="My Section",
        anchor="doc.md#my-section",
        text="Line 1\n\nLine 2\n\nLine 3\n\nLine 4\n\nLine 5"
    )
    
    chunks = chunk_section(
        section,
        doc_id="my_doc",
        source_hash="sha256:12345",
        chunk_size=15,
        chunk_overlap=5
    )
    
    assert len(chunks) > 1
    
    # Verify first chunk ID format and properties
    assert chunks[0].chunk_id == "my_doc:my-section:001"
    assert chunks[0].doc_id == "my_doc"
    assert chunks[0].section_id == "my-section"
    assert chunks[0].source_hash == "sha256:12345"
    assert chunks[0].citation_anchor == "doc.md#my-section"
    
    # Verify second chunk ID format
    assert chunks[1].chunk_id == "my_doc:my-section:002"
    assert chunks[1].doc_id == "my_doc"
    assert chunks[1].section_id == "my-section"
    assert chunks[1].source_hash == "sha256:12345"
    assert chunks[1].citation_anchor == "doc.md#my-section"

def test_chunk_document():
    sections = [
        NormalizedSection(
            section_id="",
            heading="",
            anchor="doc.md",
            text="Preamble text here."
        ),
        NormalizedSection(
            section_id="sec-one",
            heading="Section One",
            anchor="doc.md#sec-one",
            text="Section one content."
        )
    ]
    
    chunks = chunk_document(
        sections,
        doc_id="my_doc",
        source_hash="sha256:abcde",
        chunk_size=1000,
        chunk_overlap=200
    )
    
    assert len(chunks) == 2
    assert chunks[0].chunk_id == "my_doc::001"
    assert chunks[0].citation_anchor == "doc.md"
    assert chunks[0].text == "Preamble text here."
    
    assert chunks[1].chunk_id == "my_doc:sec-one:001"
    assert chunks[1].citation_anchor == "doc.md#sec-one"
    assert chunks[1].text == "Section one content."

def test_resolve_path_traversal_repo(tmp_path):
    repo_dir = tmp_path / "git_repo"
    (repo_dir / ".git").mkdir(parents=True)
    
    orig_cwd = os.getcwd()
    try:
        os.chdir(str(repo_dir))
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path("../outside.txt", "repo_file")
            
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path("/absolute/outside.txt", "repo_file")
    finally:
        os.chdir(orig_cwd)

def test_resolve_path_traversal_local(tmp_path):
    base = str(tmp_path / "base")
    os.makedirs(base, exist_ok=True)
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        resolve_source_path("../outside.txt", "local_file", base_dir=base)

def test_normalize_markdown_docstrings():
    markdown = """# Main Header
Some code block:
```python
def my_func():
    \"\"\"
    Docstring comment
    ```
    This is indented 4 spaces backticks inside docstring
    ```
    # This Python comment must NOT be a heading
    \"\"\"
    pass
```
# Next Header
Some more text.
"""
    sections = normalize_markdown(markdown, "docs/doc.md")
    headers = [s.heading for s in sections if s.heading]
    assert headers == ["Main Header", "Next Header"]

def test_chunk_overlap_validation():
    section = NormalizedSection(
        section_id="sec",
        heading="Sec",
        anchor="doc.md#sec",
        text="Some text"
    )
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=100, chunk_overlap=100)
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=100, chunk_overlap=101)

def test_emoji_only_heading_disambiguation():
    content = """# 🚀
First emoji-only heading text.

# 🚀
Second emoji-only heading text.

# 💡
Third emoji-only heading.
"""
    sections = normalize_markdown(content, "doc.md")
    headings = [s.heading for s in sections if s.heading]
    assert headings == ["🚀", "🚀", "💡"]
    
    slugs = [s.section_id for s in sections if s.heading]
    assert slugs == ["heading", "heading-1", "heading-2"]

def test_fetch_source_nfc_normalization(tmp_path):
    decomposed = "e\u0301" # NFD
    composed = "\u00e9" # NFC
    
    test_file = tmp_path / "nfd_test.md"
    test_file.write_text(decomposed, encoding="utf-8")
    
    source = SourceModel(
        source_id="test_nfc",
        type="local_file",
        path=str(test_file),
        title="NFC Test",
        citation_base="docs/nfd_test.md"
    )
    
    fetched = fetch_source(source)
    assert fetched.content == composed
    
    expected_hash = "sha256:" + hashlib.sha256(composed.encode("utf-8")).hexdigest()
    assert fetched.source_hash == expected_hash
