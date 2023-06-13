import argparse
import os
from typing import Tuple

import media_library as ml
from media_library import Entries, SortPointer

gb_no_action = False
gb_verbose = False
gb_write_csv = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trim file.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv", help="Write CSV.")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="verbose.")
    parser.add_argument("-w", action="store_true", default=False, dest="write_file", help="Write master_filelist.")
    args = parser.parse_args()
    return args


def find_original(master: list[Entries], sorted_pointers: list[SortPointer], target: Entries) -> Tuple[bool, int]:
    found = True
    start = 0
    while found:
        found, fp_index = ml.check_pointers_to_original_size(sorted_pointers, target.original_size, start)
        if found and (master[fp_index].name == target.name):
            return (found, fp_index)
        start = fp_index
    return (False, 0)


def process_targets(master: list[Entries], sorted_pointers: list[SortPointer], target: list[Entries]) -> list[Entries]:
    for item in target:
        item_path = os.path.join(item.path, item.name)
        found, orig_index = find_original(master, sorted_pointers, item)
        if found:
            if gb_verbose:
                print(f"Found original entry - {orig_index}: {master[orig_index].name}")
        else:
            ml.exit_error(f"Original entry for {item.name} not found.")

        curr_file_path = os.path.join(master[orig_index].path, master[orig_index].name)
        try:
            os.stat(curr_file_path)
        except OSError:
            ...
        else:
            if gb_verbose:
                print(f"Moving {curr_file_path} to trash.")
            if not gb_no_action:
                ml.move_file(curr_file_path, os.path.join(master[orig_index].path, "DelLinks"), gb_verbose, gb_no_action)
        if gb_verbose:
            print(f"Copying backup file {item_path} to {master[orig_index].path}")
        if not gb_no_action:
            ml.copy_file(item_path, curr_file_path, gb_verbose, gb_no_action)

        master[orig_index].current_duration = ml.file_duration(curr_file_path)
        master[orig_index].current_size = int(os.stat(curr_file_path).st_size)
        master[orig_index].ino = int(os.stat(curr_file_path).st_ino)
        if master[orig_index].csum != "":
            master[orig_index].csum = ml.checksum(curr_file_path)
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

    master = process_targets(master, ml.pointer_sort_database(master, "original_size"), target)

    if args.write_file:
        master.sort(key=lambda x: getattr(x, "current_size"))
        ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
