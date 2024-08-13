import argparse
import logging
import os
import shutil
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Tuple
from urllib.parse import urlencode, urlunparse, urlparse

import requests
import toml

"""This script monitors the disk usage of specified directories.

TL;DR: Deletes files and subdirectories to free space, sends notifications of deleted items.

1. There are three settings in the config file: directories, threshold_limit, and gotify_url/gotify_token.
    - directories: A comma separated list of directories to monitor (at least one is required).
        - The directories a required to be on the same disk.
    - threshold_limit: The minimum free space in GiB required for the script to execute.
        - A number larger than 0 is required.
    - gotify_url/gotify_token: The Gotify URL and token.
        - Not required.
2. The directories and threshold_limit settings are required.
3. The configuration file should be placed at ~/.config/disk_usage_monitor/.
4. It should be named disk_usage_monitor.ini. The config file should be in TOML format.
5. The log file will also be placed in ~/.config/disk_usage_monitor/.

### My reasoning:
The intent of this script is to prevent the disk containing the specified paths from becoming full as a lot of
unattended actions occur that copy, move, or downloads files to the disk. The necessity of the subdirectories and
files located in the specified paths has an expiration, that's why they are removed in chronological order,
oldest to newest.

### How it works:
When the script runs, it will check if the free disk space is >= the specified threshold (desired minimum free space).
If the free disk space is > the specified threshold, the script does nothing and exits. If the disk free space is <= to
the specified threshold, it will execute.

Once executed, it will get a list of files and subdirectories from the monitored directories and delete them from
oldest to newest based on 'last modified time' until the specified threshold is reached.
(desired_free_space = existing_free_space + minimum_number_of_oldest_files).
 
 ### WARNING:
USE WITH EXTREME CAUTION, THIS SCRIPT IS INTENDED TO DELETE FILES AND DIRECTORIES!
USE WITH EXTREME CAUTION, THIS SCRIPT IS INTENDED TO DELETE FILES AND DIRECTORIES!
"""

script_dir = os.path.expanduser('~/.config/dum/')
if not os.path.exists(script_dir):
    os.makedirs(script_dir)


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
                for dirpath, _, filenames in os.walk(entry.path):
                    for f in filenames:
                        fp: str = os.path.join(dirpath, f)
                        total_size += os.stat(fp).st_size
                files_data.append({'item': (entry.path, total_size, entry.stat().st_mtime)})
        return files_data


class DiskAnalyzer:
    """Analyzes disk usage of files and subdirectories until specified threshold is reached."""

    def __init__(self, dirs: List[str], threshold: int, label_mapping: Dict[str, str]) -> None:
        self.dirs: list = dirs
        self.mount_point: str = os.path.commonpath(dirs)
        self.free_space: float = self.get_disk_free_space()
        self.threshold: int = self.gib_to_bytes(threshold)
        self.label_mapping: dict = label_mapping

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
        for dir_path in self.dirs:
            handler = DirectoryHandler(dir_path)
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


class ConfigLoader:
    _config_keys = {
        'Directories': '_validate_directories',
        'ThresholdLimit': '_validate_threshold_limit',
        'GotifyURL': '_validate_gotify_url',
        'GotifyToken': '_validate_gotify_token',
    }

    def __init__(self, config_path: str) -> None:
        self.config_path: str = config_path
        self.parsed_config = toml.load(config_path)
        self.config: dict = {}
        self.load_config()

    def load_config(self) -> None:
        config_file = os.path.join(self.config_path, 'dum.toml')
        if not os.path.exists(config_file):
            raise FileNotFoundError(f'Configuration file required to execute script: {config_file}')

        try:
            self.config = toml.load(config_file)
            logging.info(self.config)
            self.validate_config()
            self.validate_gotify_config()
        except (toml.TomlDecodeError, Exception) as err:
            logging.exception(f'Error parsing the configuration file: {err}')
            self.handle_parsing_error(config_file)
            sys.exit(1)

    def validate_config(self):
        for key, method in self._config_keys.items():
            validation_method = getattr(self, method)
            logging.info(self.config.get(key))
            validation_method(self.config.get(key))

    def _get_value(self, key: str):
        return self.parsed_config.get('DEFAULT', key)

    def _validate_directories(self, dirs) -> None:
        """Check if provided directories are valid and on same physical disk."""
        if not dirs:
            raise ValueError('No directories specified.')
        elif not all(os.path.isdir(dir_path) for dir_path in dirs):
            raise ValueError(f'One or more of your directories do not exist:\n{" ".join(dirs)}')
        else:
            first_dir_device_id = os.stat(dirs[0]).st_dev
            for dir_path in dirs[1:]:
                if os.stat(dir_path).st_dev != first_dir_device_id:
                    raise ValueError('Directories are not on the same disk!')

        self.config['dirs'] = dirs

    def _validate_threshold_limit(self, threshold_limit_str) -> None:
        """Check if ThresholdLimit is a positive integer."""
        if threshold_limit_str is None or not threshold_limit_str.isdigit():
            raise ValueError('`threshold_limit` must be a positive integer.')

        threshold_limit = int(threshold_limit_str)
        if threshold_limit < 1:
            raise ValueError('`threshold_limit` must be greater than 0.')

        self.config['threshold_limit'] = threshold_limit

    def _validate_gotify_url(self, gotify_url) -> None:
        """Check if Gotify server is provided."""
        if not gotify_url:
            self.config['gotify_url'] = None
        else:
            self.config['gotify_url'] = gotify_url

    def _validate_gotify_token(self, gotify_token) -> None:
        """Check if Gotify token is provided."""
        if not gotify_token:
            self.config['gotify_token'] = None
        else:
            self.config['gotify_token'] = gotify_token

    def validate_gotify_config(self) -> None:
        """Check if Gotify server and token are provided."""
        if not self.config['gotify_url'] and not self.config['gotify_token']:
            logging.info('Gotify URL and Token are not provided. Notifications will not be sent.')
        if not self.config['gotify_url'] or not self.config['gotify_token']:
            raise ValueError(
                'It appears either `GotifyURL` or `GotifyToken` is specified but not the other. '
                'Both must be specified or both must be empty.'
                ' You can remove the section entirely if you don\'t need it.')

    def handle_parsing_error(self, config_file: str) -> None:  # noqa: no-self-use
        """Handle parsing errors by logging specific line errors."""
        with open(config_file, 'r') as f:
            line_number = 1
            for line in f:
                if line.strip().endswith('\\') and not line.rstrip().endswith('\\'):
                    logging.error(f'Line {line_number}: Trailing whitespace after line continuation character')
                elif not line.strip().startswith(';') and line.strip() and '=' not in line and '[' not in line:
                    logging.error(
                        f'Line {line_number}: No equal sign or section header found in non-comment/non-empty line. '
                        f'If this is a continuation line, make sure it begins with a space or tab character.'
                    )
                line_number += 1


def setup_logging(config_path) -> None:
    """Configure logging."""
    log_file_name = 'dum.log'
    log_file = os.path.join(config_path, log_file_name)

    # Append a new line to the log file only if it's not empty - for readability
    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        with open(log_file, 'a') as file:
            file.write('\n')

    log_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )

    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    log_handler.setFormatter(log_formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)


def send_notification(data: List[str], url: str, token: str):
    """
    Gotify notification

    Arguments:
    - data (list): List of strings to send.
    - url (str): Gotify server URL.
    - token (str): Gotify application token.
    """

    api_endpoint = 'message'  # Gotify API endpoint
    params = {'token': token}
    url = urlunparse(
        urlparse(url)._replace(
            path=api_endpoint, query=urlencode(params))
    )

    message = '\n\n'.join(data)  # for readability
    params = {
        'title': 'Disk Usage Monitor Alert',
        'message': message,
        'priority': 5,
    }

    response = requests.post(url, data=params)
    try:
        response.raise_for_status()
    except requests.HTTPError as http_err:
        logging.exception(f'HTTP error occurred: {http_err}', stack_info=True)
    except Exception as err:
        logging.exception(f'HTTP exception occurred: {err}', stack_info=True)


def main(config_path: str, dry_run: bool = False):
    """
    Define the directories to be examined and the threshold for the sum of the sizes of
    processed files/dirs together with the remaining free disk space.
    `threshold_limit` is expected to be specified in GiB
    """
    expand_user = os.path.expanduser(config_path)
    config_file = os.path.join(expand_user, 'dum.toml')

    try:
        config_loader = toml.load(config_file)

        dirs = config_loader['Directories']
        threshold_limit = config_loader['ThresholdLimit']
        gotify_url = config_loader['GotifyURL']
        gotify_token = config_loader['GotifyToken']

        # labels are the lowest level directory names in monitored directories
        # used for logging, easier to know from where something is deleted
        labels = [
            os.path.basename(_.rstrip(os.sep)).capitalize()
            for _ in dirs
        ]
        dir_labels = dict(zip(dirs, labels))

        analyzer = DiskAnalyzer(dirs, threshold_limit, dir_labels)
    except (ValueError, FileNotFoundError) as err:
        logging.exception(f'An error occurred during configuration: {str(err)}', stack_info=True)
        return 1

    try:
        processed_items = analyzer.analyze()
        processed_items_count = len(processed_items)

        if not processed_items:
            logging.info('Disk usage is below threshold. No files will be deleted.')
            return 0

        elif not dry_run:
            logging.info(f'Processing {processed_items_count} items.')
            analyzer.delete_files(processed_items)
            if gotify_url and gotify_token:
                send_notification(processed_items, gotify_url, gotify_token)
            else:
                logging.info('Gotify not configured, no notification sent.')
            return 0
        else:
            logging.info('Dry run is enabled, no changes made to the filesystem.\n'
                         f'The following {processed_items_count} items would be deleted:')
            for item in processed_items:
                logging.info(f'{item}')
            logging.info('Dry run complete.')

    except Exception as err:
        logging.exception(f'An error occurred: {str(err)}', stack_info=True)
        return 1

    except KeyboardInterrupt as err:
        logging.exception(f'Keyboard interrupt: {str(err)}', stack_info=True)
        return 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Optional argument for script path.')
    parser.add_argument(
        '--config-path',
        default='~/.config/dum/',
        help='Path to script configuration file. If unspecified, will default to "~/.config/dum"',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run the script without making any changes to the filesystem.'
             ' Gotify config will still be validated if provided with no notification sent.',
    )
    args = parser.parse_args()
    config_path = os.path.expanduser(args.config_path)
    if not os.path.exists(config_path):
        try:
            os.makedirs(config_path)
        except Exception as e:
            logging.exception(f'An error occurred: {str(e)}', stack_info=True)
            sys.exit(str(e))

    setup_logging(config_path)
    exit_code = main(config_path, dry_run=args.dry_run)
    sys.exit(exit_code)
