import os
import pytest
from pydantic import ValidationError
from ses.curation.registry import SourceRegistry, SourceModel
from ses.curation.manifest import NamespaceManifest
from ses.curation.validators import validate_freshness, validate_quality
from ses.curation.chunker import CurationChunk

def test_validate_freshness_success(tmp_path):
    # Setup files
    file_a = tmp_path / "a.md"
    file_a.write_text("# Heading A\nThis is content A.\n", encoding="utf-8")
    
    registry = SourceRegistry(
        namespace="public:validate-fresh",
        sources=[
            SourceModel(
                source_id="a",
                type="local_file",
                path=str(file_a),
                title="Title A",
                citation_base="a.md"
            )
        ]
    )
    
    # Pre-calculate hash
    import hashlib
    content = "# Heading A\nThis is content A.\n"
    source_hash = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    manifest = NamespaceManifest(
        namespace="public:validate-fresh",
        version="1.0.0",
        source_hashes={str(file_a): source_hash}
    )
    
    # 1. Freshness is 1.0
    score = validate_freshness(registry, manifest)
    assert score == 1.0
    
    # 2. Modify file content -> freshness should be 0.0
    file_a.write_text("# Heading A\nModified content A.\n", encoding="utf-8")
    score_modified = validate_freshness(registry, manifest)
    assert score_modified == 0.0
    
    # Check raise_on_error
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        validate_freshness(registry, manifest, raise_on_error=True)

def test_validate_freshness_missing_file(tmp_path):
    registry = SourceRegistry(
        namespace="public:validate-fresh-missing",
        sources=[
            SourceModel(
                source_id="nonexistent",
                type="local_file",
                path="nonexistent.md",
                title="Missing",
                citation_base="nonexistent.md"
            )
        ]
    )
    
    manifest = NamespaceManifest(
        namespace="public:validate-fresh-missing",
        version="1.0.0",
        source_hashes={"nonexistent.md": "sha256:123"}
    )
    
    score = validate_freshness(registry, manifest)
    assert score == 0.0
    
    with pytest.raises(ValueError, match="source file does not exist"):
        validate_freshness(registry, manifest, raise_on_error=True)

def test_validate_quality_gate():
    # Valid chunks
    chunks = [
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="doc",
            section_id="sec",
            text="chunk text content",
            citation_anchor="doc.md#sec",
            source_hash="sha256:abc"
        )
    ]
    
    # Should not raise any error
    validate_quality(chunks, "public:test")
    
    # 1. Empty namespace
    with pytest.raises(ValueError, match="missing_namespace"):
        validate_quality(chunks, "")
        
    # 2. Empty chunks list
    with pytest.raises(ValueError, match="empty_chunks"):
        validate_quality([], "public:test")
        
    # 3. Empty text chunk
    bad_chunks_1 = [
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="doc",
            section_id="sec",
            text="",
            citation_anchor="doc.md#sec",
            source_hash="sha256:abc"
        )
    ]
    with pytest.raises(ValueError, match="empty_chunks"):
        validate_quality(bad_chunks_1, "public:test")
        
    # 4. Duplicate chunk IDs
    bad_chunks_2 = [
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="doc",
            section_id="sec",
            text="text 1",
            citation_anchor="doc.md#sec",
            source_hash="sha256:abc"
        ),
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="doc",
            section_id="sec",
            text="text 2",
            citation_anchor="doc.md#sec",
            source_hash="sha256:abc"
        )
    ]
    with pytest.raises(ValueError, match="duplicate_chunk_ids"):
        validate_quality(bad_chunks_2, "public:test")
        
    # 5. Missing source hash
    bad_chunks_3 = [
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="doc",
            section_id="sec",
            text="text 1",
            citation_anchor="doc.md#sec",
            source_hash=""
        )
    ]
    with pytest.raises(ValueError, match="missing_source_hash"):
        validate_quality(bad_chunks_3, "public:test")
        
    # 6. Missing citation anchor
    bad_chunks_4 = [
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="doc",
            section_id="sec",
            text="text 1",
            citation_anchor="",
            source_hash="sha256:abc"
        )
    ]
    with pytest.raises(ValueError, match="missing_citation_anchor"):
        validate_quality(bad_chunks_4, "public:test")

    # 7. Missing doc_id
    bad_chunks_5 = [
        CurationChunk(
            chunk_id="doc:sec:001",
            doc_id="",
            section_id="sec",
            text="text 1",
            citation_anchor="doc.md#sec",
            source_hash="sha256:abc"
        )
    ]
    with pytest.raises(ValueError, match="missing_doc_id"):
        validate_quality(bad_chunks_5, "public:test")
