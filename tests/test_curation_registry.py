import pytest
import yaml
from unittest.mock import patch
from pydantic import ValidationError

from ses.curation.registry import (
    SourceModel,
    SourceRegistry,
    load_registry_from_file,
    load_registries_from_dir,
    load_all_registries,
    get_registry_paths
)

def test_valid_parsing(tmp_path):
    yaml_content = """
namespace: public:ses-docs
publisher: SES
trust_level: official
update_policy: on_commit
sources:
  - source_id: readme
    type: local_file
    path: README.md
    title: SES README
    citation_base: README.md
"""
    file_path = tmp_path / "valid_registry.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")
    
    registry = load_registry_from_file(str(file_path))
    
    assert registry.namespace == "public:ses-docs"
    assert registry.id == "public:ses-docs"
    assert registry.publisher == "SES"
    assert registry.trust_level == "official"
    assert registry.update_policy == "on_commit"
    
    assert len(registry.sources) == 1
    source = registry.sources[0]
    assert source.source_id == "readme"
    assert source.type == "local_file"
    assert source.path == "README.md"
    assert source.title == "SES README"
    assert source.citation_base == "README.md"

def test_invalid_yaml_syntax(tmp_path):
    invalid_yaml = """
namespace: public:ses-docs
publisher: : invalid syntax
"""
    file_path = tmp_path / "invalid_syntax.yaml"
    file_path.write_text(invalid_yaml, encoding="utf-8")
    
    with pytest.raises(yaml.YAMLError):
        load_registry_from_file(str(file_path))

def test_missing_fields_validation_registry(tmp_path):
    # Missing required namespace field
    missing_fields_yaml = """
publisher: SES
sources: []
"""
    file_path = tmp_path / "missing_fields.yaml"
    file_path.write_text(missing_fields_yaml, encoding="utf-8")
    
    with pytest.raises(ValidationError) as excinfo:
        load_registry_from_file(str(file_path))
    assert "namespace" in str(excinfo.value)

def test_missing_fields_validation_source(tmp_path):
    # Missing required fields in source (source_id)
    missing_source_fields_yaml = """
namespace: public:ses-docs
sources:
  - type: local_file
    path: README.md
    title: SES README
    citation_base: README.md
"""
    file_path = tmp_path / "missing_source_fields.yaml"
    file_path.write_text(missing_source_fields_yaml, encoding="utf-8")
    
    with pytest.raises(ValidationError) as excinfo:
        load_registry_from_file(str(file_path))
    assert "source_id" in str(excinfo.value)

def test_empty_file_validation(tmp_path):
    file_path = tmp_path / "empty.yaml"
    file_path.write_text("", encoding="utf-8")
    
    with pytest.raises(ValueError) as excinfo:
        load_registry_from_file(str(file_path))
    assert "is empty" in str(excinfo.value)

def test_non_dict_yaml_validation(tmp_path):
    file_path = tmp_path / "list.yaml"
    file_path.write_text("- item1\n- item2", encoding="utf-8")
    
    with pytest.raises(ValueError) as excinfo:
        load_registry_from_file(str(file_path))
    assert "must contain a YAML mapping" in str(excinfo.value)

def test_get_registry_paths():
    with patch("ses.curation.registry.BUILTIN_REGISTRIES_DIR", "/fake/builtin"), \
         patch("ses.curation.registry.CURATION_REGISTRIES_DIR", "/fake/custom"):
        paths = get_registry_paths()
        # Verify both are included, builtin first, custom second
        assert len(paths) == 2
        assert paths[0] == "/fake/builtin"
        assert paths[1] == "/fake/custom"

def test_get_registry_paths_deduplication():
    # If custom dir is same as builtin
    with patch("ses.curation.registry.BUILTIN_REGISTRIES_DIR", "/fake/common"), \
         patch("ses.curation.registry.CURATION_REGISTRIES_DIR", "/fake/common"):
        paths = get_registry_paths()
        assert len(paths) == 1
        assert paths[0] == "/fake/common"

def test_loader_priorities_and_overriding(tmp_path):
    builtin_dir = tmp_path / "builtin"
    custom_dir = tmp_path / "custom"
    
    builtin_dir.mkdir()
    custom_dir.mkdir()
    
    # 1. Built-in registry
    builtin_yaml = """
namespace: public:ses-docs
publisher: BuiltinPublisher
trust_level: official
sources: []
"""
    # 2. Built-in other registry
    builtin_other_yaml = """
namespace: public:other-docs
publisher: BuiltinOtherPublisher
trust_level: official
sources: []
"""
    # 3. Custom overriding registry
    custom_yaml = """
namespace: public:ses-docs
publisher: CustomPublisher
trust_level: custom_official
sources: []
"""
    
    (builtin_dir / "ses_docs.yaml").write_text(builtin_yaml, encoding="utf-8")
    (builtin_dir / "other_docs.yaml").write_text(builtin_other_yaml, encoding="utf-8")
    (custom_dir / "ses_docs.yaml").write_text(custom_yaml, encoding="utf-8")
    
    # Patch the directories
    with patch("ses.curation.registry.BUILTIN_REGISTRIES_DIR", str(builtin_dir)), \
         patch("ses.curation.registry.CURATION_REGISTRIES_DIR", str(custom_dir)):
        
        registries = load_all_registries()
        
        # Verify that both namespaces exist
        assert "public:ses-docs" in registries
        assert "public:other-docs" in registries
        
        # Verify overriding namespace: public:ses-docs is overridden by custom publisher
        assert registries["public:ses-docs"].publisher == "CustomPublisher"
        assert registries["public:ses-docs"].trust_level == "custom_official"
        
        # Verify other namespace was not touched
        assert registries["public:other-docs"].publisher == "BuiltinOtherPublisher"
