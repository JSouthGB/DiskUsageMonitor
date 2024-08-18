import os
from typing import List, Dict, Tuple


class DirectoryHandler:
    """Collects paths, last modified time, and size of files and subdirectories (and their contents)."""

    def __init__(self, dir_path) -> None:
        self.dir_path: str = dir_path

    def gather_files_data(self) -> List[Dict[str, Tuple[str, int, float]]]:
        """
        Each file or directory is represented as a dictionary, where the key 'item' maps to a tuple.
        The tuple consists of the file/directory path, its size in bytes, and its last modification time.

        Returns:
            - A list of dictionaries, containing previously noted data.
        """
        files_data = []

        for entry in os.scandir(self.dir_path):
            if entry.is_file():
                files_data.append({'item': (entry.path, entry.stat().st_size, entry.stat().st_mtime)})
            elif entry.is_dir():
                # If the entry is a directory, calculate its total size by walking through
                # the directory recursively and summing the sizes of all contained files.
                total_size = 0
                for path_walk, _, filenames in os.walk(entry.path):
                    for f in filenames:
                        fp: str = os.path.join(path_walk, f)
                        total_size += os.stat(fp).st_size
                files_data.append({'item': (entry.path, total_size, entry.stat().st_mtime)})
        return files_data
