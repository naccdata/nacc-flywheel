from flywheel.models.file_entry import FileEntry


class Acquisition:

    def get_file(self, name: str) -> FileEntry:
        ...
