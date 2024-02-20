"""Tests for Directory Conflicts."""
import yaml
from redcap.nacc_directory import DirectoryConflict


# pylint: disable=too-few-public-methods
class TestDirectoryConflict:
    """Tests for directory conflicts."""

    # pylint: disable=no-self-use
    def test_conflict(self):
        """tests dumping a directory conflict."""
        conflict = DirectoryConflict(user_id='dummy',
                                     conflict_type='identifier',
                                     entries=[])

        output = yaml.safe_dump(data=[conflict],
                                allow_unicode=True,
                                default_flow_style=False)
        assert output == ('- conflict_type: identifier\n'
                          '  entries: []\n  user_id: dummy\n')
