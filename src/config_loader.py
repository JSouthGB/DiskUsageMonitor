import logging
import os
import sys

import toml

from src import config_path


class ConfigLoader:
    _config_keys = {
        'Directories': '_validate_directories',
        'ThresholdLimit': '_validate_threshold_limit',
        'GotifyURL': '_validate_gotify_url',
        'GotifyToken': '_validate_gotify_token',
    }

    def __init__(self) -> None:
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
        except (toml.TomlDecodeError, Exception) as err:
            logging.exception(f'Error parsing the configuration file: {err}')
            self.handle_parsing_error(config_file)
            sys.exit(1)

    def get_directories(self):
        """Validate and return directories."""
        dirs = self.parsed_config.get('DEFAULT', "Directories")
        self._validate_directories(dirs)
        return dirs

    def get_threshold_limit(self):
        """Validate and return threshold limit."""
        threshold_limit = self.parsed_config.get('DEFAULT', 'ThresholdLimit')
        self._validate_threshold_limit(threshold_limit)
        return threshold_limit

    def get_gotify(self):
        gotify_url = self.parsed_config.get('DEFAULT', 'GotifyURL')
        gotify_token = self.parsed_config.get('DEFAULT', 'GotifyToken')
        if self._validate_gotify(gotify_url, gotify_token):
            return gotify_url, gotify_token
        else:
            return None, None

    def _validate_directories(self, dirs) -> None:
        """Check if directories are specified, valid, and on same physical disk."""
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

    def _validate_gotify(self, gotify_url, gotify_token) -> bool:  # noqa: no-self-use
        """Check if Gotify server and token are provided."""
        if gotify_url and gotify_token:
            return True
        elif not all((gotify_url, gotify_token)):
            return False
        else:
            if not gotify_url or not gotify_token:
                raise ValueError(
                    'It appears either `GotifyURL` or `GotifyToken` is specified but not the other. '
                    'Both must be specified or both must be empty.'
                    ' You can remove the section entirely if you don\'t need it.'
                )

    def handle_parsing_error(self, config_file: str) -> None:  # noqa: no-self-use
        """Handle parsing errors by logging specific line errors."""
        with open(config_file, 'r') as file:
            line_number = 1
            for line in file:
                if line.strip().endswith('\\') and not line.rstrip().endswith('\\'):
                    logging.error(f'Line {line_number}: Trailing whitespace after line continuation character')
                elif not line.strip().startswith(';') and line.strip() and '=' not in line and '[' not in line:
                    logging.error(
                        f'Line {line_number}: No equal sign or section header found in non-comment/non-empty line. '
                        f'If this is a continuation line, make sure it begins with a space or tab character.'
                    )
                line_number += 1
