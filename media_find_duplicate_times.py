import argparse
import operator
import os
import re
import subprocess
import time

import ahocorasick_rs as ah
import getch
import media_library as ml

import pdb


def get_args():

    parser = argparse.ArgumentParser(description="Search for entries.")
    #    parser.add_argument("target_strings", nargs="+")
    parser.add_argument("-m", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument(
        "-f",
        type=str,
        dest="first_names_file_input_path",
        default="female_first_names.txt",
    )
    parser.add_argument("-l", type=str, dest="full_names_file_input_path", default="full_names.txt")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument("-p", action="store_true", default=False, dest="print_path", help="Print path.")
    parser.add_argument("-s", type=float, dest="start_length", default=0.0)
    parser.add_argument(
        "-t",
        action="store_true",
        default=False,
        dest="sort_time",
        help="Sort based on original duration.",
    )
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    args = parser.parse_args()
    return args


def get_YN(question: str) -> bool:
    print(f" {question} (Y/N)", flush=True)
    while True:
        response = getch.getch()
        match response.upper():
            case "Y":
                return True
            case "N":
                return False


def get_12PQS() -> str:
    print(f"(1 - Delete File 1   2 - Delete File 2   Z-Play   Q-uit   S-kip", flush=True)
    while True:
        response = getch.getch()
        if response.upper() in "12ZQS":
            return response.upper()


def embed_names(master: list[ml.Entries], ns: ml.NameSearch):
    """
    Search each entry in master, finding hits against a list of targets.
    Enbed the names in the entry.
    """
    name_refs = {}
    unlisted_name_refs = {}
    vendors = {}
    for i, item in enumerate(master):
        vendor = ml.get_vendor(item.name)
        if "vendor" not in master[i].data.keys():
            master[i].data["vendor"] = vendor
        found_names = ml.search_names(item.name, ns)
        if "artists" not in master[i].data.keys():
            master[i].data["artists"] = []
        for full_name in found_names:
            if full_name.listed == True:
                master[i].data["artists"].append(full_name.name)
    return master


def build_command(*args):
    command = [args[0]]
    if len(args) > 1:
        for i in args[1:]:
            command.append(i)
    return command


def run_viewer(path_1: str, path_2: str, skip_time: int = 0):

    pid = subprocess.Popen(
        build_command("vlc", "--start-time=" + str(skip_time), path_1, path_2),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid.wait()


def process_combo(master: list[ml.Entries], i: int, last_i: int):

    while True:
        response = get_12PQS()
        match response:
            case "1":
                ml.move_file(
                    os.path.join(master[last_i].path, master[last_i].name),
                    os.path.join(os.path.dirname(master[last_i].path), "DelLinks"),
                )
                return
            case "2":
                ml.move_file(
                    os.path.join(master[i].path, master[i].name),
                    os.path.join(os.path.dirname(master[i].path), "DelLinks"),
                )
                return
            case "Z":
                run_viewer(
                    os.path.join(master[last_i].path, master[last_i].name),
                    os.path.join(master[i].path, master[i].name),
                    100,
                )
            case "Q":
                quit()
            case "S":
                return


def main():

    args = get_args()

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    master.sort(key=operator.attrgetter("original_duration"))
    name_search = ml.prepare_name_search(args.first_names_file_input_path, args.full_names_file_input_path)
    master = embed_names(master, name_search)
    last_length = 0.0
    last_i = 0
    for i, item in enumerate(master):
        length = master[i].original_duration
        if (abs(length - last_length) >= 0.000 and abs(length - last_length) < 0.001) and (
            master[last_i].data["vendor"] == "Unknown" or master[i].data["vendor"] == "Unknown"
        ):
            if length < args.start_length or (
                master[i].data["vendor"] == "" ### <----- Fill in as needed for popular vendor
                and (sorted(master[i].data["artists"]) != sorted(master[last_i].data["artists"]))
            ):
                ...
            else:
                print(
                    f"{master[last_i].original_size:12d} :: {master[last_i].original_duration:10f} :: {master[last_i].name} "
                )
                print(f"{master[i].original_size:12d} :: {master[i].original_duration:10f} :: {master[i].name} ")
                print()
                process_combo(master, i, last_i)
                print()
        last_i = i
        last_length = length


if __name__ == "__main__":
    main()
