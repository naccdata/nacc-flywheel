"""Tests for handling of YAML documents."""
import yaml
from inputs.yaml import get_object_lists_from_stream


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
        object_list = get_object_lists_from_stream(yaml_object, 'empty-list')
        assert object_list == [[]]
