import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import time
import uuid

import media_library as ml

gb_no_action = False
gb_verbose = False


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
    parser.add_argument("-e", type=str, dest="end_trim_length", default="00:00:00", help="End trim length (HH:MM:SS).")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument(
        "-s", type=str, dest="start_trim_length", default="00:00:00", help="Start trim length (HH:MM:SS)."
    )
    parser.add_argument(
        "-t", action="store_true", default=False, dest="tag_modified", help="Add original duration to filename."
    )
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    args = parser.parse_args()
    return args


def str_to_td(string):
    dt_result = dt.datetime.strptime(string, "%H:%M:%S")
    return dt.timedelta(hours=dt_result.hour, minutes=dt_result.minute, seconds=dt_result.second)


def move_file(source, target):
    if gb_verbose:
        print(f"move_file {source} -> {target}")
    if not gb_no_action:
        try:
            shutil.move(source, target)
        except OSError as e:
            exit_error(f"Trimmed file move failed: {e}")
    return os.stat(target)


def main():
    global gb_no_action
    global gb_verbose

    args = get_args()
    if args.verbose:
        gb_verbose = args.verbose
    if args.no_action:
        gb_no_action = args.no_action
    target_path = args.target_path[0]

    if os.path.exists(target_path):
        target = ml.create_file_entry(target_path)
    else:
        exit_error(f"Target file not found: {target_path}")

    duration = ml.file_duration(target_path)
    td_duration = dt.timedelta(seconds=float(duration))
    td_start_length = str_to_td(args.start_trim_length)
    td_end_length = str_to_td(args.end_trim_length)
    td_new_end_time = td_duration - td_end_length

    temp_outfile = str(uuid.uuid4()) + ".mp4"
    command = f'ffmpeg -i "{target_path}" -metadata comment="###MDV1### {duration} {target.current_size}" -ss {td_start_length} -to {td_new_end_time} -c:v copy -c:a copy "{temp_outfile}"'

    if gb_verbose:
        print(command)

    if not gb_no_action:
        proc_return = subprocess.run(command, shell=True)
        if proc_return.returncode != 0:
            exit_error("Trim process failed.")
        new_duration = ml.file_duration(temp_outfile)
        if args.tag_modified:
            root, ext = os.path.splitext(target_path)
            target_path = root + f" - OrLn({time.strftime('%H%M%S', time.gmtime(float(duration)))})" + ext
        move_file(temp_outfile, target_path)
        os.utime(target_path, (dt.datetime.timestamp(target.date), dt.datetime.timestamp(target.date)))
        if gb_verbose:
            print(f"Trimmed from {duration} to {new_duration}.")


if __name__ == "__main__":
    main()
