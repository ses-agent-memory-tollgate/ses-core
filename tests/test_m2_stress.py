import os
import pytest
from unittest.mock import patch

from ses.curation.fetchers import resolve_source_path, find_git_root
from ses.curation.chunker import chunk_section, chunk_document
from ses.curation.normalize import NormalizedSection
from ses.core.chunking import chunk_text
from ses.curation.registry import SourceModel


# =====================================================================
# 1. PATH TRAVERSAL BLOCK STRESS TESTS
# =====================================================================

def test_path_traversal_various_base_paths(tmp_path):
    # Setup directories
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    
    secret_file = other_dir / "secret.txt"
    secret_file.write_text("SUPER_SECRET_KEY", encoding="utf-8")
    
    safe_file = base_dir / "safe.txt"
    safe_file.write_text("SAFE_CONTENT", encoding="utf-8")
    
    # 1. Test relative path escaping base_dir
    with pytest.raises(ValueError, match="Path traversal detected"):
        resolve_source_path("../other/secret.txt", "local_file", base_dir=str(base_dir))
        
    # 2. Test absolute path escaping base_dir
    with pytest.raises(ValueError, match="Path traversal detected"):
        resolve_source_path(str(secret_file), "local_file", base_dir=str(base_dir))
        
    # 3. Test absolute path inside base_dir (should be allowed)
    resolved = resolve_source_path(str(safe_file), "local_file", base_dir=str(base_dir))
    assert os.path.realpath(resolved) == os.path.realpath(str(safe_file))
    
    # 4. Test relative path inside base_dir (should be allowed)
    resolved_rel = resolve_source_path("safe.txt", "local_file", base_dir=str(base_dir))
    assert os.path.realpath(resolved_rel) == os.path.realpath(str(safe_file))

    # 5. Test nested subdirectory inside base_dir (should be allowed)
    sub_dir = base_dir / "subdir"
    sub_dir.mkdir()
    sub_file = sub_dir / "nested.txt"
    sub_file.write_text("NESTED_CONTENT", encoding="utf-8")
    
    resolved_nested = resolve_source_path("subdir/nested.txt", "local_file", base_dir=str(base_dir))
    assert os.path.realpath(resolved_nested) == os.path.realpath(str(sub_file))

    # 6. Test traversal attempt inside nested directory but escaping it
    # Note: resolving relative to base_dir, so "../base/subdir/nested.txt" resolves inside base_dir,
    # but "../other/secret.txt" goes outside base_dir.
    resolved_traversal_back = resolve_source_path("subdir/../safe.txt", "local_file", base_dir=str(base_dir))
    assert os.path.realpath(resolved_traversal_back) == os.path.realpath(str(safe_file))
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        resolve_source_path("subdir/../../other/secret.txt", "local_file", base_dir=str(base_dir))


def test_path_traversal_git_root(tmp_path):
    git_dir = tmp_path / "git_repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()
    
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("GIT_OUTSIDE_SECRET", encoding="utf-8")
    
    inside_file = git_dir / "inside.txt"
    inside_file.write_text("GIT_INSIDE_CONTENT", encoding="utf-8")
    
    # Mock find_git_root to return our temporary git_dir
    with patch("ses.curation.fetchers.find_git_root", return_value=str(git_dir)):
        # 1. Relative path escaping git root
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path("../outside/secret.txt", "repo_file")
            
        # 2. Absolute path escaping git root
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path(str(outside_file), "repo_file")
            
        # 3. Path inside repo (should succeed)
        resolved = resolve_source_path("inside.txt", "repo_file")
        assert os.path.realpath(resolved) == os.path.realpath(str(inside_file))


# =====================================================================
# 2. CHUNK OVERLAP VALIDATION WITH BOUNDARIES
# =====================================================================

def test_chunk_overlap_boundaries():
    section = NormalizedSection(
        section_id="sec-1",
        heading="Section 1",
        anchor="doc.md#sec-1",
        text="This is a test document to check chunk overlap boundaries."
    )
    
    # 1. overlap == size should raise ValueError
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=100, chunk_overlap=100)
        
    # 2. overlap > size should raise ValueError
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=100, chunk_overlap=101)

    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=10, chunk_overlap=50)

    # 3. overlap < size should work (even by 1 character)
    chunks = chunk_section(section, "doc", "hash", chunk_size=100, chunk_overlap=99)
    assert len(chunks) > 0

    # 4. overlap = 0 should work
    chunks_zero = chunk_section(section, "doc", "hash", chunk_size=100, chunk_overlap=0)
    assert len(chunks_zero) > 0


# =====================================================================
# 3. CHUNK MERGER OVERFLOW WITH EDGE CASE STRING SPLITS
# =====================================================================

def test_chunk_merger_overflow_various_scenarios():
    # 1. No separators available (hard-split character by character)
    # The text is 100 characters of 'a'. chunk_size=10, chunk_overlap=4.
    # We want to make sure that no returned chunk is larger than 10.
    chunks_hard = chunk_text("a" * 100, chunk_size=10, chunk_overlap=4)
    for c in chunks_hard:
        assert len(c) <= 10, f"Chunk too large: len={len(c)}, content={c}"

    # 2. Standard space separator split where tail overlap might exceed budget
    # E.g. chunks are separated by space. Let's make sure the merger logic doesn't overflow.
    text = "12345 67890 12345 67890 12345678901234567890"
    # Target chunk_size = 15, chunk_overlap = 6
    # "12345" (5), "67890" (5), "12345" (5), "67890" (5), "12345678901234567890" (20)
    chunks = chunk_text(text, chunk_size=15, chunk_overlap=6)
    for c in chunks:
         assert len(c) <= 15, f"Chunk too large: len={len(c)}, content={c}"

    # 3. String split where separator join cost causes overflow if not handled correctly
    # Let's test with multiple consecutive separators, e.g. "word1\n\n\n\nword2"
    text_newlines = "word1" + "\n\n" * 5 + "word2"
    chunks_newlines = chunk_text(text_newlines, chunk_size=10, chunk_overlap=2)
    for c in chunks_newlines:
         assert len(c) <= 10, f"Chunk too large: len={len(c)}, content={c}"

    # 4. Long word at the end that exceeds chunk size
    text_long_tail = "abcde fghij klmnopqrstuvwxyz"
    chunks_long_tail = chunk_text(text_long_tail, chunk_size=10, chunk_overlap=3)
    for c in chunks_long_tail:
         assert len(c) <= 10, f"Chunk too large: len={len(c)}, content={c}"

    # 5. Unicode character boundaries
    # Make sure length calculation works with multi-byte or emojis
    text_emoji = "🚀 🌟 🎯 💎 🔑 🍀 🌈 🌺 🌻 🍁 🍂 🌾"
    chunks_emoji = chunk_text(text_emoji, chunk_size=8, chunk_overlap=3)
    for c in chunks_emoji:
         assert len(c) <= 8, f"Chunk too large: len={len(c)}, content={c}"
