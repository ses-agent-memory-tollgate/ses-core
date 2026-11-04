import os
import pytest
import tempfile
from unittest.mock import patch
from ses.curation.fetchers import resolve_source_path, find_git_root
from ses.core.chunking import chunk_text
from ses.curation.chunker import chunk_section, NormalizedSection

# =====================================================================
# 1. Path Traversal Block Under Different Base Paths
# =====================================================================

def test_path_traversal_local_file_basic():
    base_dir = os.path.abspath("C:/Users/52999/ses/ses-core")
    
    # 1. Path inside base directory should resolve successfully
    valid_path = os.path.join(base_dir, "ses/core/chunking.py")
    res = resolve_source_path(valid_path, "local_file", base_dir=base_dir)
    assert res == os.path.realpath(valid_path)

    # 2. Path trying to escape base directory should raise ValueError
    invalid_path = os.path.join(base_dir, "../PROJECT.md")
    with pytest.raises(ValueError, match="Path traversal detected"):
        resolve_source_path(invalid_path, "local_file", base_dir=base_dir)

def test_path_traversal_local_file_various_bases():
    with tempfile.TemporaryDirectory() as tmpdir:
        real_tmpdir = os.path.realpath(tmpdir)
        
        # Test base path with trailing slash
        base_with_slash = real_tmpdir + os.sep
        
        # Path inside base
        in_path = os.path.join(real_tmpdir, "file.txt")
        # Touch file to ensure it exists if checked (though resolve_source_path doesn't check existence)
        res = resolve_source_path("file.txt", "local_file", base_dir=base_with_slash)
        assert res == os.path.realpath(in_path)
        
        # Path outside base
        out_path = os.path.join(real_tmpdir, "../outside_file.txt")
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path(out_path, "local_file", base_dir=base_with_slash)

def test_path_traversal_repo_file_basic(tmp_path):
    # Setup dummy git repo
    repo_dir = tmp_path / "dummy_git_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    
    real_repo_dir = os.path.realpath(str(repo_dir))
    
    # Mock find_git_root to return our dummy repo root
    with patch("ses.curation.fetchers.find_git_root", return_value=real_repo_dir):
        # 1. Path inside git root should be resolved
        res = resolve_source_path("src/lib.py", "repo_file")
        assert res == os.path.realpath(os.path.join(real_repo_dir, "src/lib.py"))
        
        # 2. Path outside git root should raise ValueError
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path("../outside.py", "repo_file")
            
        # 3. Absolute path outside git root should raise ValueError
        abs_outside = os.path.abspath(os.path.join(real_repo_dir, "..", "outside.py"))
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_source_path(abs_outside, "repo_file")

def test_path_traversal_relative_tricks():
    base_dir = os.path.abspath("C:/Users/52999/ses/ses-core")
    
    # Path that looks like traversal but stays inside base directory
    tricky_valid = os.path.join(base_dir, "ses/core/../core/chunking.py")
    res = resolve_source_path(tricky_valid, "local_file", base_dir=base_dir)
    assert res == os.path.realpath(os.path.join(base_dir, "ses/core/chunking.py"))

    # Traversal attempting to use null byte (not allowed in python path operations anyway)
    with pytest.raises(ValueError):
        resolve_source_path("ses/core/chunking.py\x00/../../outside.txt", "local_file", base_dir=base_dir)

# =====================================================================
# 2. Chunk Overlap Validation with Boundaries
# =====================================================================

def test_chunk_overlap_boundaries():
    section = NormalizedSection(
        section_id="sec",
        heading="Sec",
        anchor="doc.md#sec",
        text="This is a test section text for checking boundaries."
    )
    
    # 1. Normal case: chunk_overlap < chunk_size (Passes)
    chunks = chunk_section(section, "doc", "hash", chunk_size=20, chunk_overlap=10)
    assert len(chunks) > 0
    
    # 2. Edge case: chunk_overlap == 0 (Passes)
    chunks_zero = chunk_section(section, "doc", "hash", chunk_size=20, chunk_overlap=0)
    assert len(chunks_zero) > 0
    
    # 3. Boundary: chunk_overlap == chunk_size - 1 (Passes)
    chunks_boundary = chunk_section(section, "doc", "hash", chunk_size=20, chunk_overlap=19)
    assert len(chunks_boundary) > 0

    # 4. Boundary: chunk_overlap == chunk_size (Should fail)
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=20, chunk_overlap=20)
        
    # 5. Boundary: chunk_overlap > chunk_size (Should fail)
    with pytest.raises(ValueError, match="chunk_overlap must be strictly less than chunk_size"):
        chunk_section(section, "doc", "hash", chunk_size=20, chunk_overlap=21)

    # 6. Edge case: negative chunk_overlap
    # Note: chunk_section does not explicitly block negative values, but it should not crash.
    # Let's ensure it runs and does not crash, producing valid chunks.
    chunks_negative = chunk_section(section, "doc", "hash", chunk_size=20, chunk_overlap=-5)
    assert len(chunks_negative) > 0

# =====================================================================
# 3. Chunk Merger Overflow with Edge Case String Splits
# =====================================================================

def test_chunk_merger_overflow_splits():
    # 1. String splits where pieces are larger than chunk_size (triggers recursive char split)
    text_long_words = "supercalifragilisticexpialidocious antidisestablishmentarianism floccinaucinihilipilification"
    chunks = chunk_text(text_long_words, chunk_size=15, chunk_overlap=5)
    
    # Every chunk must respect chunk_size boundary
    for chunk in chunks:
        assert len(chunk) <= 15
        
    # Check that chunks reconstruct the words (ignoring spaces since splits happened on char level)
    reconstructed = "".join(chunks)
    assert "supercali" in reconstructed

def test_chunk_merger_extreme_overlap():
    # Test text where overlap is relatively large and might cause infinite loops or overflow
    text = "abc def ghi jkl mno pqr stu vwx yz"
    # Overlap is close to chunk size, pieces are small.
    # We want to make sure it doesn't produce chunks larger than chunk_size.
    chunks = chunk_text(text, chunk_size=8, chunk_overlap=6)
    for c in chunks:
        assert len(c) <= 8

def test_chunk_merger_multiple_separators():
    # Text with varying natural boundary separators
    text = "Paragraph 1.\n\nParagraph 2 with long sentence. Sentence two here.\nLine break here."
    chunks = chunk_text(text, chunk_size=30, chunk_overlap=10)
    for c in chunks:
        assert len(c) <= 30
    assert len(chunks) > 1

def test_chunk_merger_only_separators():
    # String consisting of only separators
    text = "\n\n   \n\n  "
    chunks = chunk_text(text, chunk_size=10, chunk_overlap=2)
    assert chunks == []
