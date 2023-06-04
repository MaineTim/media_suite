import argparse
import datetime as dt
import ffmpeg
import os
import shutil
import subprocess
import sys
import time
import uuid
from typing import Optional, Tuple

import media_library as ml
from media_library import Entries

master = []
gb_no_action = False
gb_verbose = False
gb_write_csv = False


def exit_error(*error_data):
    for i, data in enumerate(error_data):
        print(data, end=" ")
        if i != len(error_data) - 1:
            print(" : ", end=" ")
    print("")
    sys.exit()


def get_args():
    parser = argparse.ArgumentParser(description="Trim file.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-v", action="store_true", default=False, dest="verbose")
    parser.add_argument("-w", action="store_true", default=False, dest="write_file", help="Write master_filelist.")
    args = parser.parse_args()
    return args


def find_original(master, target, orig_duration, orig_size) -> Tuple[bool, int]:
    found = True
    start = 0
    while found:
        found, fp_index = ml.check_size(master, int(orig_size), start)
        if found and (master[fp_index].name == target.name):
            return (found, fp_index)
        start = fp_index
    return (False, 0)


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

    if not args.run_without_master:
        if (master := ml.read_master_file(master_input_path)) == []:
            exit_error(f"{master_input_path} not found and is required.")

    if os.path.exists(target_path):
        target = ml.create_file_entry(target_path)
    else:
        exit_error(f"Target file not found: {target_path}")

    orig_duration, orig_size = ml.file_md_tag(target_path)
    if orig_duration == "":
        exit_error(f"{target_path} has no mp_tag. Cannot detect original file.")
    found, orig_index = find_original(master, target, orig_duration, orig_size) 
    if found:
        print(f"Found original file: {os.path.join(master[orig_index].path, master[orig_index].name)}")

    master[orig_index].current_duration = ml.file_duration(target_path)
    master[orig_index].current_size = os.stat(target_path).st_size

    if args.write_file:
        ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
