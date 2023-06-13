import argparse
import os

import media_library as ml
from media_library import Entries

gb_no_action = False
gb_verbose = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete deleted backup files.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument("-D", type=str, dest="delete_path")
    parser.add_argument("--deleted-input-path", type=str, dest="deleted_input_path", default="deleted_filelist")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    args = parser.parse_args()
    return args


def find_inode(target_list: list[Entries], inode: int):
    for item in target_list:
        if item.ino == inode:
            return (1, item.name)
    return (0, "")


def remove_file(path: str):
    if gb_verbose:
        print(f"Deleting {path}")
    if not gb_no_action:
        try:
            os.unlink(path)
        except FileNotFoundError:
            return


def delete_found_entry(target_path: str, filename: str, item: str, inode: int):
    # Found the inode entry file, if duration matches entry, remove it.
    if gb_verbose:
        print(f"Found matching inode {inode} {item.name}: {filename}")
    if os.stat(os.path.join(target_path, filename)).st_size != item.current_size:
        if gb_verbose:
            print(f"Sizes don't match! {os.stat(os.path.join(target_path, filename)).st_size} {item.current_size}")
        return
    if abs(ml.file_duration(os.path.join(target_path, filename)) - (item.current_duration)) < 0.5:
        remove_file(os.path.join(target_path, filename))
    else:
        if gb_verbose:
            print(
                f"Durations don't match! {ml.file_duration(os.path.join(target_path, filename))} {item.current_duration}"
            )
        return


def process_deleted_entry(target_list: list[Entries], item: Entries, backup_path: str, target_path: str, inode: int):
    if os.path.exists(backup_path):
        # Found a matching name, if inode okay, then remove it.
        if gb_verbose:
            print(f"Found matching filename {backup_path}")
        backup_stat = os.stat(backup_path)
        if int(backup_stat.st_ino) == inode:
            remove_file(backup_path)
        else:
            if gb_verbose:
                print(f"Inodes don't match! Actual: {backup_stat.st_ino} Recorded:{inode}")
            return
    else:
        found, filename = find_inode(target_list, inode)
        if found:
            delete_found_entry(target_path, filename, item, inode)
        else:
            if gb_verbose:
                print(f"No backup found: {backup_path}")


def process_deleted(deleted: list[Entries], target_path: str, target_list: list[Entries]) -> None:
    for item in deleted[:]:
        for whole_path in item.paths:
            if whole_path == "":
                print(f"{os.path.join(item.path, item.name)}: No backup!")
                continue
            if gb_verbose:
                print(f"Checking {whole_path}")
            path, inode = ml.split_backup_path(whole_path)
            if path != target_path.rstrip("/"):
                continue
            backup_path = os.path.join(path, item.name)
            if os.path.exists(path):
                process_deleted_entry(target_list, item, backup_path, target_path, inode)


def main() -> None:
    global gb_no_action
    global gb_verbose

    args = get_args()

    gb_verbose = args.verbose
    gb_no_action = args.no_action

    target_path = args.target_path[0]

    if (deleted := ml.read_master_file(args.deleted_input_path)) == []:
        ml.exit_error(f"{args.deleted_input_path} not found and is required.")
    print(f"{len(deleted)} deleted records loaded.")

    if os.path.exists(target_path):
        target_list = ml.create_file_list(target_path)
        print(f"{len(target_list)} target files loaded.")
    else:
        ml.exit_error(f"{target_path} doesn't exist!")

    process_deleted(deleted, target_path, target_list)


if __name__ == "__main__":
    main()
