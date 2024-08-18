import argparse
import logging
import os
import sys

import toml

from src.logger import setup_logging
from src import config_path
from notify import send_notification
from src.disk_analyzer import DiskAnalyzer


def main(dry_run: bool = False):
    """
    Define the directories to be examined and the threshold for the sum of the sizes of
    processed files/dirs together with the remaining free disk space.
    `threshold_limit` is expected to be specified in GiB
    """
    expand_user_home_dir = os.path.expanduser(config_path)
    config_file = os.path.join(expand_user_home_dir, 'dum.toml')

    try:
        config_loader = toml.load(config_file)

        dirs = config_loader['Directories']
        threshold_limit = config_loader['ThresholdLimit']
        gotify_url = config_loader['GotifyURL']
        gotify_token = config_loader['GotifyToken']

        # labels are the lowest level directory names in monitored directories
        # used for logging, easier to identify from where something is deleted
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
    setup_logging(config_path)

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

    exit_code = main(dry_run=args.dry_run)
    sys.exit(exit_code)
