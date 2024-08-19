import logging
import os
import shutil
from datetime import datetime
from typing import List, Dict, Tuple

from src.directory_handler import DirectoryHandler
from src.config_loader import ConfigLoader


class DiskAnalyzer:
    """Analyzes disk usage of files and subdirectories until specified threshold is reached."""
    config_loader = ConfigLoader()

    def __init__(self) -> None:
        self.dirs: List[str] = self.config_loader.get_directories()
        self.threshold_limit: int = self.config_loader.get_threshold_limit()
        self.mount_point: str = os.path.commonpath(self.dirs)
        self.free_space: float = self.get_disk_free_space()
        self.threshold: int = self.gib_to_bytes(self.threshold_limit)
        self.label_mapping: dict = self.get_labels()

    @staticmethod
    def gib_to_bytes(gib: int) -> int:
        """
        Convert GiB (gibibytes) to bytes.
        Formula: Gibibytes = Bytes / 1024^3
        """
        return gib * (1024 ** 3)

    @staticmethod
    def bytes_to_gib(_bytes: int) -> float:
        """
        Convert Bytes to GiB (gibibytes).
        Formula: Byte = GiB * 1024^3
        """
        return _bytes / (1024 ** 3)

    def get_labels(self) -> Dict[str, str]:
        """
        Gets the labels of directories.
        """
        # labels are the lowest level directory names in monitored directories
        # used for logging, easier to identify from where something is deleted
        labels = [
            os.path.basename(_.rstrip(os.sep)).capitalize()
            for _ in self.dirs
        ]
        return dict(zip(self.dirs, labels))

    def get_disk_free_space(self) -> int:
        """
        Gets the free disk space of the common mount point of directories.

        Returns:
        - The free disk space in bytes.
        """
        stats = os.statvfs(self.mount_point)
        return stats.f_frsize * stats.f_bavail

    def format_items(self, item):
        path = os.path.normpath(item['item'][0])
        path_split = path.split(os.sep)

        label = 'No_label'
        for dir_name, assigned_label in self.label_mapping.items():
            if dir_name in path:
                label = assigned_label
                break

        size_in_gib: float = self.bytes_to_gib(item['item'][1])
        mod_time = datetime.fromtimestamp(item['item'][2]).strftime('%Y-%m-%d %H:%M:%S')
        message = f'{label}: {path_split[-1]}, Size: {size_in_gib:0.2f} GiB, Modified: {mod_time}'
        return message

    def analyze(self) -> List[str]:
        """
        Examines the directories and logs the path, size and last modification time of each file or subdirectory
        deleted. The examination stops when the total size of the deleted files and directories together with
        the existing free disk space reach the threshold set.
        """
        if self.free_space >= self.threshold:
            processed_items = []
            return processed_items

        all_items: List[Dict[str, Tuple[str, int, float]]] = []

        handler = DirectoryHandler()
        all_items.extend(handler.gather_files_data())

        sorted_items: List[Dict[str, Tuple[str, int, float]]] = sorted(all_items, key=lambda x: x['item'][2])
        total_size = 0

        processed_items = []
        for item in sorted_items:
            total_size += item['item'][1]
            message = self.format_items(item)
            processed_items.append(message)

            if total_size >= (self.threshold - self.free_space):
                break
        return processed_items

    def delete_files(self, files_to_delete) -> None:
        """
        Deletes files from the filesystem.

        Args:
        - files_to_delete (list): List of file paths to delete.
        """
        for file_path in files_to_delete:
            label = file_path.split(': ')[0]
            label_removed = file_path.split(': ')[1]
            name = label_removed.split(', ')[0]
            try:
                for dir_path, labels in self.label_mapping.items():
                    if label == labels:
                        working_dir = os.path.join(dir_path, name)

                        if os.path.isfile(working_dir):
                            os.remove(working_dir)
                            logging.info(f'Deleted: {file_path}')
                            break
                        elif os.path.isdir(working_dir):
                            shutil.rmtree(working_dir)
                            logging.info(f'Deleted: {file_path}')
                            break
                        else:
                            logging.error(f'Unrecognized path: {working_dir}')

            except Exception as err:
                logging.exception(f'Failed to delete {file_path}: {err}', stack_info=True)
