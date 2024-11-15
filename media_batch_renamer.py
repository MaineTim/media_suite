import argparse
import os
import shutil
from typing import Tuple

import media_library as ml

gb_no_action = False
gb_target_path = ""
gb_verbose = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename backup files.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument(
        "-i", type=str, dest="master_input_path", default="master_filelist"
    )
    parser.add_argument(
        "-n", action="store_true", default=False, dest="no_action", help="No action."
    )
    parser.add_argument(
        "-v", action="store_true", default=False, dest="verbose", help="Verbose."
    )
    args = parser.parse_args()
    return args


def path_inode(item: ml.Entries) -> Tuple[bool, int]:
    for path in item.paths:
        if path[: path.find("[")] == gb_target_path:
            return True, int(path[path.find("[") + 1 : path.find("]")])
    return False, 0


def check_master(master: list[ml.Entries], target_item: ml.Entries) -> Tuple[bool, int]:
    _, result = ml.check_original_size(master, target_item.original_size)
    while True:
        if (
            result >= len(master)
            or master[result].original_size != target_item.original_size
        ):
            return False, 0
        if master[result].name == target_item.name:
            return False, result
        found, inode = path_inode(master[result])
        if (
            found
            and inode == target_item.ino
            and master[result].name != target_item.name
        ):
            return True, result
        if (
            abs(
                ml.file_duration(os.path.join(target_item.path, target_item.name))
                - master[result].original_duration
            )
            < 0.5
        ):
            return True, result
        if ml.checksum(
            os.path.join(master[result].path, master[result].name)
        ) == ml.checksum(os.path.join(gb_target_path, target_item.name)):
            return True, result
        result += 1


def rename_file(orig: ml.Entries, target: ml.Entries) -> None:
    if gb_verbose:
        print(f"Moving {os.path.join(gb_target_path, orig.name)} -> {target.name}\n")
    if not gb_no_action:
        shutil.move(
            os.path.join(gb_target_path, orig.name),
            os.path.join(gb_target_path, target.name),
        )


def main() -> None:
    global gb_no_action
    global gb_target_path
    global gb_verbose

    args = get_args()
    gb_target_path = args.target_path[0]
    gb_verbose = args.verbose
    gb_no_action = args.no_action

    if gb_target_path[-1] != "/":
        gb_target_path = gb_target_path + "/"

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")
    master.sort(key=lambda x: getattr(x, "original_size"))

    if os.path.exists(gb_target_path):
        target_list = ml.create_file_list(gb_target_path)
        print(f"{len(target_list)} target files loaded.")
    else:
        ml.exit_error(f"{gb_target_path} doesn't exist!")

    for item in target_list:
        needs_rename, result = check_master(master, item)
        if needs_rename:
            if gb_verbose:
                print(item.name)
                print(master[result].name)
            rename_file(item, master[result])


if __name__ == "__main__":
    main()
