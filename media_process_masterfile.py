import argparse
import bisect
import datetime
import operator
import os
from typing import Tuple

import media_library as ml
from media_library import Entries

# import getch


NOENTRY = 0
MASTER = 1
QUARENTINE = 2

gb_verbose = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a database of files for the given directory.")
    parser.add_argument("target_paths", nargs="+")
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv", help="Write CSV.")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    args = parser.parse_args()
    return args


def check_current_fs_status(master: list[Entries]) -> Tuple[list[Entries], list[Entries]]:
    """Keep only extant entries, quarentine the others."""
    quarentine = []
    for item in master[:]:
        item_path = os.path.join(item.path, item.name)
        # Entry no long on the filesystem, quarentine it.
        if not os.path.exists(item_path):
            print(f"{item.name} doesn't exist, quarentined.")
            quarentine.append(item)
            master.remove(item)
        # Entry has changed size, bail so user can investigate.
        elif (size := os.stat(item_path).st_size) != item.current_size:
            ml.exit_error(f"{item.name} has changed size from {item.current_size} to {size}.")
    print(f"{len(master)} records loaded.")
    return (master, quarentine)


def build_current_fs_path_list(target_paths: list[str]) -> list[str]:
    """Return a merged list of files to process."""
    file_paths = []
    for target_path in target_paths:
        print(f"Scanning {target_path}...")
        files = [
            os.path.join(target_path, f)
            for f in os.listdir(target_path)
            if os.path.isfile(os.path.join(target_path, f)) and os.path.splitext(f)[1] in [".mp4", ".mp4~"]
        ]
        print(f"{len(files)} files found.")
        file_paths.extend(files)
    print(f"{len(file_paths)} target files loaded.")
    return file_paths


def search_file_path(master: list[Entries], quarentine: list[Entries], file_path: str) -> Tuple[int, int]:
    """Find the instance of a file in databases if there is one."""
    fp_stat = os.stat(file_path)
    found = True
    start = 0
    # Look in master by size and name, then inode and size.
    while found:
        found, fp_index = ml.check_current_size(master, fp_stat.st_size, start)
        if found and (os.path.join(master[fp_index].path, master[fp_index].name) == file_path):
            return (MASTER, fp_index)
        start = fp_index
    found, fp_index = ml.check_inode_in_path(master, os.path.dirname(file_path), fp_stat.st_ino)
    if found and (master[fp_index].current_size == fp_stat.st_size):
        return (MASTER, fp_index)
    # Look in quarentine by inode and size, then size and mtime.
    found, fp_index = ml.check_inode_in_path(quarentine, os.path.dirname(file_path), fp_stat.st_ino)
    if found and (quarentine[fp_index].current_size == fp_stat.st_size):
        return (QUARENTINE, fp_index)
    found = True
    start = 0
    while found:
        found, fp_index = ml.check_current_size(quarentine, fp_stat.st_size, start)
        if found and (
            quarentine[fp_index].date == datetime.datetime.fromtimestamp(fp_stat.st_mtime, tz=datetime.timezone.utc)
        ):
            return (QUARENTINE, fp_index)
        start = fp_index
    return (NOENTRY, 0)


def process_targets(master: list[Entries], quarentine: list[Entries], target_paths: list[str]) -> list[Entries]:
    """Main list processing loop."""
    entry_size = operator.attrgetter("current_size")
    for file_path in target_paths:
        found_db, index = search_file_path(master, quarentine, file_path)
        if gb_verbose:
            print(f"{file_path} : {found_db} - {index}")
        if found_db == QUARENTINE:
            print(f"{quarentine[index].name} -> {file_path} updated")
            quarentine[index].name = os.path.basename(file_path)
            quarentine[index].ino = os.stat(file_path).st_ino
            bisect.insort(master, quarentine[index], key=entry_size)
        if found_db == NOENTRY:
            new_entry = ml.create_file_entry(file_path, update_duration=True)
            bisect.insort(master, new_entry, key=entry_size)
    return master


def main() -> None:
    global gb_verbose

    args = get_args()
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path

    gb_verbose = args.verbose

    if (master := ml.read_master_file(args.master_input_path)) != []:
        master.sort(key=lambda x: getattr(x, "current_size"))
        master, quarentine = check_current_fs_status(master)
    target_paths = build_current_fs_path_list(args.target_paths)
    master = process_targets(master, quarentine, target_paths)

    ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
