import argparse
import copy
import datetime as dt
import os

import media_library as ml
from media_library import Entries, SortPointer

gb_no_action = False
gb_verbose = False
gb_write_csv = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trim file.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument(
        "-b",
        type=str,
        dest="original_dir",
        required=True,
        default="",
        help="Original file backup dir (required).",
    )
    parser.add_argument(
        "-d", action="store_true", default=False, dest="write_csv", help="Write CSV."
    )
    parser.add_argument(
        "-i", type=str, dest="master_input_path", default="master_filelist"
    )
    parser.add_argument(
        "-n", action="store_true", default=False, dest="no_action", help="No action."
    )
    parser.add_argument(
        "-r",
        action="store_true",
        default=False,
        dest="replace_backup_files",
        help="Replace backups.",
    )
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument(
        "-v", action="store_true", default=False, dest="verbose", help="verbose."
    )
    parser.add_argument(
        "-w",
        action="store_true",
        default=False,
        dest="write_file",
        help="Write master_filelist.",
    )
    args = parser.parse_args()
    return args


def replace_backups(item: Entries) -> Entries:
    new_entry = copy.deepcopy(item)
    new_entry.backups = 0
    new_entry.paths = []
    for whole_path in item.paths[:]:
        path, inode = ml.split_backup_path(whole_path)
        backup_path = os.path.join(path, item.name)
        if os.path.exists(path):
            if os.path.exists(backup_path):
                backup_stat = os.stat(backup_path)
                # Backup inode doesn't match.
                if backup_stat.st_ino != inode:
                    ml.exit_error(
                        f"{backup_path} backup inode {backup_stat.st_ino} doesn't match entry {inode}."
                    )
            ml.copy_file(
                os.path.join(item.path, item.name),
                backup_path,
                gb_verbose,
                gb_no_action,
            )
            backup_ptr = ml.make_backup_path_entry(
                path, int(os.stat(backup_path).st_ino)
            )
            if backup_ptr not in new_entry.paths:
                new_entry.backups += 1
                new_entry.paths.append(backup_ptr)
        else:
            ml.exit_error(
                f"{backup_path} backup doesn't exist. {item.backups} backups listed."
            )
    if new_entry.backups > 0:
        return new_entry
    return item


def process_targets(
    master: list[Entries],
    sorted_pointers: list[SortPointer],
    target: list[Entries],
    original_dir: str,
    replace_backup_files: bool,
) -> list[Entries]:
    for item in target:
        item_path = os.path.join(item.path, item.name)
        found, orig_index = ml.check_pointers_to_name(sorted_pointers, item.name)
        if found:
            if gb_verbose:
                print(
                    f"Found original file: {os.path.join(master[orig_index].path, master[orig_index].name)}"
                )
        else:
            ml.exit_error(f"Original entry for {item.name} not found.")

        master_path = os.path.join(master[orig_index].path, item.name)

        ml.move_file(master_path, original_dir, gb_verbose, gb_no_action)
        ml.move_file(item_path, master_path, gb_verbose, gb_no_action)
        os.utime(
            master_path,
            (
                dt.datetime.timestamp(master[orig_index].date),
                dt.datetime.timestamp(master[orig_index].date),
            ),
        )

        master_stat = os.stat(master_path)

        if master[orig_index].original_size == master[orig_index].current_size:
            master[orig_index].original_size = int(master_stat.st_size)
            master[orig_index].current_size = int(master_stat.st_size)
        else:
            master[orig_index].current_size = int(master_stat.st_size)
        if master[orig_index].original_duration == master[orig_index].current_duration:
            master[orig_index].original_duration = float(ml.file_duration(master_path))
            master[orig_index].current_duration = master[orig_index].original_duration
        else:
            master[orig_index].current_duration = float(ml.file_duration(master_path))
        master[orig_index].ino = int(master_stat.st_ino)
        if master[orig_index].csum != "":
            master[orig_index].csum = ml.checksum(master_path)

        if replace_backup_files:
            master[orig_index] = replace_backups(master[orig_index])
    return master


def main() -> None:
    global gb_no_action
    global gb_verbose

    args = get_args()
    if args.verbose:
        gb_verbose = args.verbose
    if args.no_action:
        gb_no_action = args.no_action
    master_input_path = args.master_input_path
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = master_input_path
    target_path = args.target_path[0]

    if (master := ml.read_master_file(master_input_path)) == []:
        ml.exit_error(f"{master_input_path} not found and is required.")

    if os.path.exists(target_path):
        target = ml.create_file_list(target_path)
    else:
        ml.exit_error(f"Target not found: {target_path}")

    master = process_targets(
        master,
        ml.pointer_sort_database(master, "name"),
        target,
        args.original_dir,
        args.replace_backup_files,
    )

    if args.write_file:
        master.sort(key=lambda x: getattr(x, "current_size"))
        ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
