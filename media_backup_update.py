import argparse
import bisect
import operator
import os
import sys
from typing import Any

import media_library as ml


def exit_error(*error_data: Any) -> None:
    for i, data in enumerate(error_data):
        print(data, end=" ")
        if i != len(error_data) - 1:
            print(" : ", end=" ")
    print("")
    sys.exit()


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update database with backup information.")
    parser.add_argument("backup_path", nargs=1)
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-v", action="store_true", default=False, dest="verbose")
    args = parser.parse_args()
    return args


def check_master_files(master: list[ml.Entries], curr: ml.Entries) -> int:
    entry_size = operator.attrgetter("current_size")

    result = bisect.bisect_left(master, curr.current_size, key=entry_size)
    while True:
        if result == len(master) or master[result].current_size != curr.current_size:
            return -1
        if master[result].name == curr.name:
            return result
        result += 1


def main() -> None:

    args = get_args()
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path
    backup_path = args.backup_path[0]

    if backup_path[-1] != "/":
        backup_path = backup_path + "/"

    if (master := ml.read_master_file(args.master_input_path)) == []:
        exit_error(f"{args.master_input_path} not found and is required.")

    if os.path.exists(backup_path):
        working = ml.create_file_list(backup_path)
        print(f"{len(working)} target files loaded.")
    else:
        exit_error(f"{backup_path} doesn't exist!")

    change_count = 0
    for item in working:
        result = check_master_files(master, item)
        if result != -1:
            inode = item.ino
            item = master[result]
            backup_ptr = ml.make_backup_path_entry(backup_path, inode)
            if backup_ptr not in item.paths:
                master[result].backups += 1
                master[result].paths.append(backup_ptr)
                change_count += 1
                if args.verbose:
                    print(master[result])
        else:
            print(f"{item.name} not found in master file.")
    print(f"{change_count} records updated.")
    ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
