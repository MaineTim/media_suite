import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import time
import uuid

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
    parser.add_argument("-e", type=str, dest="end_trim_length", default="00:00:00")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-r", action="store_true", default=False, dest="run_without_master")
    parser.add_argument("-s", type=str, dest="start_trim_length", default="00:00:00")
    parser.add_argument("-t", action="store_true", default=False, dest="tag_modified")
    parser.add_argument("-v", action="store_true", default=False, dest="verbose")
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

    if not args.run_without_master:
        found, result = ml.check_db(master, target)
        if not found:
            exit_error("Master entry not found: {target}")

    duration = ml.file_duration(target_path)
    td_duration = dt.timedelta(seconds=float(duration))
    td_start_length = str_to_td(args.start_trim_length)
    td_end_length = str_to_td(args.end_trim_length)
    td_new_end_time = td_duration - td_end_length

    temp_outfile = str(uuid.uuid4()) + ".mp4"
    command = (
        f'ffmpeg -i "{target_path}" -ss {td_start_length} -to {td_new_end_time} -c:v copy -c:a copy "{temp_outfile}"'
    )

    if gb_verbose:
        print(command)

    if not gb_no_action:
        proc_return = subprocess.run(command, shell=True)
        if proc_return.returncode != 0:
            exit_error("Trim process failed.")
        new_duration = ml.file_duration(temp_outfile)
        if args.tag_modified:
            root, ext = os.path.splitext(target_path)
            target_path = root + f" - OrLn({time.strftime('%H%M%S', time.gmtime(float(new_duration)))})" + ext
        move_file(temp_outfile, target_path)
        os.utime(target_path, (dt.datetime.timestamp(target.date), dt.datetime.timestamp(target.date)))
        stat_entry = os.stat(target_path)
        if gb_verbose:
            print(f"Trimmed from {duration} to {new_duration}.")
        if not args.run_without_master:
            old = master[result]
            new_data = old.data
            if args.tag_modified:
                target_name = os.path.basename(target_path)
                new_data["untrimmed name"] = old.name
            else:
                target_name = old.name
            new = Entries(
                UID=old.UID,
                path=old.path,
                name=target_name,
                original_size=old.original_size,
                current_size=stat_entry.st_size,
                date=dt.datetime.fromtimestamp(stat_entry.st_mtime, tz=dt.timezone.utc),
                backups=old.backups,
                paths=old.paths,
                original_duration=old.original_duration,
                current_duration=new_duration,
                ino=stat_entry.st_ino,
                nlink=stat_entry.st_nlink,
                csum=0,
                data=new_data,
            )
            master[result] = new
            ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
