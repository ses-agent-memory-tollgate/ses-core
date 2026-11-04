import os
import pytest
from pydantic import ValidationError
from ses.curation.manifest import NamespaceManifest, load_manifest_from_file, save_manifest_to_file

def test_manifest_pydantic_validation():
    # Valid minimum manifest
    m = NamespaceManifest(
        namespace="public:test",
        version="1.0.0",
        source_hashes={"file.md": "sha256:abc"}
    )
    assert m.namespace == "public:test"
    assert m.version == "1.0.0"
    assert m.source_hashes == {"file.md": "sha256:abc"}
    assert m.status == "staging"
    assert m.chunk_count == 0
    assert m.published_at is None

    # Invalid manifest - missing namespace
    with pytest.raises(ValidationError):
        NamespaceManifest(version="1.0.0")

    # Invalid manifest - missing version
    with pytest.raises(ValidationError):
        NamespaceManifest(namespace="public:test")

def test_manifest_save_and_load(tmp_path):
    m = NamespaceManifest(
        namespace="public:test-save",
        version="2026-06-22.1",
        publisher="TestPublisher",
        trust_level="official",
        source_hashes={"a.md": "sha256:123", "b.md": "sha256:456"},
        chunk_count=15,
        status="staging"
    )
    
    filepath = str(tmp_path / "manifest.json")
    save_manifest_to_file(m, filepath)
    
    assert os.path.exists(filepath)
    
    loaded = load_manifest_from_file(filepath)
    assert loaded.namespace == "public:test-save"
    assert loaded.version == "2026-06-22.1"
    assert loaded.publisher == "TestPublisher"
    assert loaded.trust_level == "official"
    assert loaded.source_hashes == {"a.md": "sha256:123", "b.md": "sha256:456"}
    assert loaded.chunk_count == 15
    assert loaded.status == "staging"

def test_manifest_load_not_found():
    with pytest.raises(FileNotFoundError):
        load_manifest_from_file("nonexistent_manifest.json")
