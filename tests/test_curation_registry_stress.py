import os
import pytest
import yaml
from unittest.mock import patch
from pydantic import ValidationError

from ses.curation.registry import (
    SourceModel,
    SourceRegistry,
    load_registry_from_file,
    load_registries_from_dir,
    load_all_registries
)

def test_valid_yaml_various_string_stylings(tmp_path):
    yaml_content = """
namespace: "public:double-quoted"
publisher: 'single-quoted'
trust_level: |
  official-level
  with-newline
update_policy: >
  on-commit-folded
sources:
  - source_id: "id-1"
    type: "local"
    path: "path/to/file.md"
    title: "Title with Unicode: 🚀"
    citation_base: "Base Title"
"""
    file_path = tmp_path / "string_stylings.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")
    
    registry = load_registry_from_file(str(file_path))
    assert registry.namespace == "public:double-quoted"
    assert registry.publisher == "single-quoted"
    # PyYAML parser will preserve newline for | and fold for >
    assert registry.trust_level.strip() == "official-level\nwith-newline"
    assert registry.update_policy.strip() == "on-commit-folded"
    assert registry.sources[0].title == "Title with Unicode: 🚀"


def test_valid_yaml_empty_sources(tmp_path):
    # 1. Explicit empty list
    yaml_content_1 = """
namespace: public:empty-sources-1
sources: []
"""
    file_path_1 = tmp_path / "empty_1.yaml"
    file_path_1.write_text(yaml_content_1, encoding="utf-8")
    registry_1 = load_registry_from_file(str(file_path_1))
    assert registry_1.namespace == "public:empty-sources-1"
    assert registry_1.sources == []

    # 2. Omitted sources list (should default to list)
    yaml_content_2 = """
namespace: public:empty-sources-2
"""
    file_path_2 = tmp_path / "empty_2.yaml"
    file_path_2.write_text(yaml_content_2, encoding="utf-8")
    registry_2 = load_registry_from_file(str(file_path_2))
    assert registry_2.namespace == "public:empty-sources-2"
    assert registry_2.sources == []


def test_valid_yaml_with_extra_ignored_fields(tmp_path):
    yaml_content = """
namespace: public:extra-fields
extra_root_field: "this should be ignored"
nested_extra_map:
  key1: val1
  key2: val2
sources:
  - source_id: id-extra
    type: local
    path: path.md
    title: Title
    citation_base: citation
    extra_source_field: "ignored too"
"""
    file_path = tmp_path / "extra_fields.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")
    
    registry = load_registry_from_file(str(file_path))
    assert registry.namespace == "public:extra-fields"
    assert len(registry.sources) == 1
    assert registry.sources[0].source_id == "id-extra"


def test_invalid_yaml_incorrect_types(tmp_path):
    # namespace must be a string, passing a dictionary should fail validation
    yaml_content_1 = """
namespace:
  nested: dict
sources: []
"""
    file_path_1 = tmp_path / "bad_type_1.yaml"
    file_path_1.write_text(yaml_content_1, encoding="utf-8")
    with pytest.raises(ValidationError):
        load_registry_from_file(str(file_path_1))

    # sources must be a list, passing a string should fail validation
    yaml_content_2 = """
namespace: public:bad-sources
sources: "not a list"
"""
    file_path_2 = tmp_path / "bad_type_2.yaml"
    file_path_2.write_text(yaml_content_2, encoding="utf-8")
    with pytest.raises(ValidationError):
        load_registry_from_file(str(file_path_2))

    # source path must be a string, passing a list should fail validation
    yaml_content_3 = """
namespace: public:bad-source-field
sources:
  - source_id: id-1
    type: local
    path:
      - list
      - path
    title: Title
    citation_base: citation
"""
    file_path_3 = tmp_path / "bad_type_3.yaml"
    file_path_3.write_text(yaml_content_3, encoding="utf-8")
    with pytest.raises(ValidationError):
        load_registry_from_file(str(file_path_3))


def test_malformed_yaml_syntax(tmp_path):
    # Extremely malformed YAML structure (e.g. mapping key duplicate, invalid colons, formatting)
    yaml_content = """
namespace: public:malformed
publisher: {unbalanced braces
  nested: value
"""
    file_path = tmp_path / "malformed.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_registry_from_file(str(file_path))


def test_non_existent_file():
    with pytest.raises(FileNotFoundError):
        load_registry_from_file("this/file/does/not/exist.yaml")


def test_permission_denied_file_reading(tmp_path):
    file_path = tmp_path / "no_permission.yaml"
    file_path.write_text("namespace: public:no-permission\n", encoding="utf-8")
    
    # Mock open to raise PermissionError when opening this file
    original_open = open
    def mock_open(file, *args, **kwargs):
        if str(file) == str(file_path):
            raise PermissionError("[Errno 13] Permission denied")
        return original_open(file, *args, **kwargs)
        
    with patch("builtins.open", mock_open):
        with pytest.raises(PermissionError):
            load_registry_from_file(str(file_path))


def test_permission_denied_directory_listing(tmp_path):
    # Mock os.listdir to raise PermissionError for a target directory
    def mock_listdir(path):
        raise PermissionError("[Errno 13] Permission denied")
        
    with patch("os.listdir", mock_listdir):
        with pytest.raises(PermissionError):
            load_registries_from_dir(str(tmp_path))


def test_non_existent_directory():
    # If a directory does not exist, load_registries_from_dir should return empty dict
    res = load_registries_from_dir("this/directory/does/not/exist")
    assert res == {}
