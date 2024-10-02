"""Tests for handling of YAML documents."""
from io import StringIO

import yaml
from inputs.yaml import get_object_lists_from_stream, load_from_stream


# pylint: disable=(too-few-public-methods)
class TestYAML:
    """Test for handling of YAML documents."""

    # pylint: disable=(no-self-use)
    def test_empty(self):
        """Test for empty list.

        Function called returns list of lists.
        """
        empty_list = []
        yaml_object = yaml.safe_dump(empty_list,
                                     allow_unicode=True,
                                     default_flow_style=False)
        yaml_stream = StringIO()
        yaml_stream.write(yaml_object)
        object_list = get_object_lists_from_stream(yaml_stream)
        assert object_list is not None
        assert [doc for doc in object_list] == []

        yaml_stream.seek(0)
        yaml_object = load_from_stream(yaml_stream)
        assert yaml_object == []

    def test_load_all(self):
        yaml_stream = StringIO()
        yaml_stream.write("---\n"
                          "k1: v1\n"
                          "k2: v2\n"
                          "---\n"
                          "k1: v1\n"
                          "k2: v2\n")
        yaml_stream.seek(0)
        yaml_iterator = get_object_lists_from_stream(yaml_stream)
        object_list = [object for object in yaml_iterator]
        assert object_list == [{
            'k1': 'v1',
            'k2': 'v2'
        }, {
            'k1': 'v1',
            'k2': 'v2'
        }]
