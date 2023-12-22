import yaml

from redcap.nacc_directory import DirectoryConflict


class TestDirectoryConflict:

    def test_conflict(self):
        conflict = DirectoryConflict(user_id='dummy', conflict_type='identifier', entries=[])

        output = yaml.safe_dump(data=[conflict], allow_unicode=True, default_flow_style=False)
        assert output == '- conflict_type: identifier\n  entries: []\n  user_id: dummy\n'

