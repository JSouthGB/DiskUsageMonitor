## DUM - Disk Usage Monitor

This script will free up disk space on a single disk. One or more directories may be monitored, as
long as they're on the same disk. 

TL;DR: Deletes files and subdirectories on a single disk from one or more monitored directories to free up disk space,
sends notifications of deleted items.

1. There are three settings in the config file: directories, threshold_limit, and gotify_url/gotify_token.
    - directories: A comma separated list of directories to monitor (at least one is required).
        - The directories are required to be on the same disk.
    - threshold_limit: The minimum free space in GiB required for the script to execute.
        - A number larger than 0 is required.
    - gotify_url/gotify_token: The Gotify URL and token.
        - Not required.
2. The directories and threshold_limit settings are required.
3. The configuration file should be placed at ~/.config/disk_usage_monitor/disk_usage_monitor.toml.
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

Once executed, a list of files and subdirectories from the monitored directories will be created and deleted from
oldest to newest based on 'last modified time' until the specified threshold is reached.
(desired_free_space = existing_free_space + minimum_number_of_oldest_files).
 
 ### WARNING:
USE WITH EXTREME CAUTION, THIS SCRIPT IS INTENDED TO DELETE FILES AND DIRECTORIES!

### ToDo
- [ ] Implement job scheduling
- [ ] Create bare config file on first run.
- [ ] Add support for specifying log directory.
- [ ] Add sum of deleted files/directories.
- [ ] Implement support for multiple disks.
- [ ] Consider [shoutrrr](https://github.com/containrrr/shoutrrr/) support.
