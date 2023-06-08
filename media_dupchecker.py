import argparse
import os
import shutil
import sys
from typing import Any, Tuple

import media_library as ml

gb_no_action = False
gb_verbose = False
gb_write_csv = False


def exit_error(*error_data: Any) -> None:
    for i, data in enumerate(error_data):
        print(data, end=" ")
        if i != len(error_data) - 1:
            print(" : ", end=" ")
    print("")
    sys.exit()


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check for duplicate files against database.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv", help="Write CSV.")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-m", action="store_true", default=False, dest="move_original", help="Move existing files.")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    args = parser.parse_args()
    return args


def move_file(target_path: str, target: ml.Entries) -> None:
    if not os.path.exists(os.path.join(target_path, "m4a_Trash")) and not gb_no_action:
        os.mkdir(os.path.join(target_path, "m4a_Trash"))
    if gb_verbose:
        print(f"move_file {os.path.join(target.path, target.name)}")
    if not gb_no_action:
        shutil.move(os.path.join(target.path, target.name), os.path.join(target_path, "m4a_Trash"))


def check_target(target_path: str, master: list[ml.Entries], item: ml.Entries) -> Tuple[bool, int]:
    found, result = ml.check_db(master, item)
    if found:
        return found, result
    found, result = ml.check_original_size(master, item.original_size)
    if found:
        checksum = ml.checksum(os.path.join(target_path, item.name))
        target_found = False
        while not target_found:
            if ml.checksum(os.path.join(master[result].path, master[result].name)) == checksum:
                return found, result
            if gb_verbose:
                print(f"Master entry: {master[result].name}")
                print(f"Target file: {item.name}")
                print("Files are same size.\n")
            found, result = ml.check_original_size(master, item.original_size, result)
            if not found:
                return False, 0
    return False, 0


def main() -> None:
    global gb_no_action
    global gb_verbose
    global gb_write_csv

    args = get_args()
    target_path = args.target_path[0]
    gb_write_csv = args.write_csv
    gb_verbose = args.verbose
    gb_no_action = args.no_action

    if (master := ml.read_master_file(args.master_input_path)) == []:
        exit_error(f"{args.master_input_path} not found and is required.")
    master.sort(key=lambda x: getattr(x, "original_size"))   

    if os.path.exists(target_path):
        target_list = ml.create_file_list(target_path)
        print(f"{len(target_list)} target files loaded.")
    else:
        exit_error(f"{target_path} doesn't exist!")

    for item in target_list:
        found, result = check_target(target_path, master, item)
        if found:
            if gb_verbose:
                print(f"Master entry: {os.path.join(master[result].path, master[result].name)}")
                print(f"Target file: {os.path.join(item.path, item.name)}")
            if args.move_original:
                move_file(target_path, master[result])
            else:
                move_file(target_path, item)
            if gb_verbose:
                print()


if __name__ == "__main__":
    main()
