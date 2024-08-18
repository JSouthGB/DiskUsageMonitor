import logging
import os
from logging.handlers import RotatingFileHandler


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
