import logging
import os
import sys

import toml

from src import config_path


class ConfigLoader:
    def __init__(self) -> None:
        self.parsed_config: dict = {}
        self.load_config()
        
    def load_config(self) -> None:
        config_file = os.path.join(config_path, "dum.toml")
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file required to execute script: {config_file}")
        try:
            self.parsed_config = toml.load(config_file)
            logging.info(self.parsed_config)
        except (toml.TomlDecodeError, Exception) as err:
            logging.exception(f"Error parsing the configuration file: {err}")
            self.handle_parsing_error(config_file)
            sys.exit(1)

    def get_directories(self):
        """Validate and return directories."""
        dirs = self.parsed_config["Directories"]
        self._validate_directories(dirs)
        return dirs

    def get_threshold_limit(self):
        """Validate and return threshold limit."""
        threshold_limit = self.parsed_config["ThresholdLimit"]
        self._validate_threshold_limit(threshold_limit)
        return threshold_limit

    def get_gotify(self):
        """Validate and return Gotify URL and token."""
        return self._validate_gotify()

    def _validate_directories(self, dirs) -> None:
        """Check if directories are specified, valid, and on same physical disk."""
        if not dirs:
            raise ValueError("No directories specified.")
        elif not all(os.path.isdir(dir_path) for dir_path in dirs):
            raise ValueError(f"One or more of your directories do not exist:\n{' '.join(dirs)}")
        else:
            first_dir_device_id = os.stat(dirs[0]).st_dev
            for dir_path in dirs[1:]:
                if os.stat(dir_path).st_dev != first_dir_device_id:
                    raise ValueError("Directories are not on the same disk!")

        self.parsed_config["dirs"] = dirs

    def _validate_threshold_limit(self, threshold_limit_str) -> None:
        """Check if ThresholdLimit is a positive integer."""
        if threshold_limit_str is None or threshold_limit_str <= 0:
            raise ValueError("`threshold_limit` must be a positive integer.")

        threshold_limit = int(threshold_limit_str)
        if threshold_limit < 1:
            raise ValueError("`threshold_limit` must be greater than 0.")

        self.parsed_config["threshold_limit"] = threshold_limit

    def _validate_gotify(self) -> tuple:
        """Check if Gotify server and token are provided."""
        if ("GotifyURL" in self.parsed_config) != ("GotifyToken" in self.parsed_config):
            raise ValueError(
                "\nIt appears either `GotifyURL` or `GotifyToken` is specified but not the other. \n"
                "Both must be specified or both must be empty.\n"
                "You can remove the section entirely if you don\'t need it."
            )
        if "GotifyURL" in self.parsed_config and "GotifyToken" in self.parsed_config:
            gotify_url = self.parsed_config["GotifyURL"]
            gotify_token = self.parsed_config["GotifyToken"]
            return gotify_url, gotify_token
        else:
            return None, None

    def handle_parsing_error(self, config_file: str) -> None:  # noqa: no-self-use
        """Handle parsing errors by logging specific line errors."""
        with open(config_file, "r") as file:
            line_number = 1
            for line in file:
                if line.strip().endswith("\\") and not line.rstrip().endswith("\\"):
                    logging.error(f"Line {line_number}: Trailing whitespace after line continuation character")
                elif not line.strip().startswith(";") and line.strip() and "=" not in line and "[" not in line:
                    logging.error(
                        f"Line {line_number}: No equal sign or section header found in non-comment/non-empty line. "
                        f"If this is a continuation line, make sure it begins with a space or tab character."
                    )
                line_number += 1
