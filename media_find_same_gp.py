import argparse
import itertools
import operator
import os
import platform
import re
import subprocess
import time

import ahocorasick_rs as ah
import getch
import media_library as ml
import psutil

import pdb

gridplayer_path = "/Volumes/Macintosh HD/Applications/GridPlayer.app/Contents/MacOS/GridPlayer"

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


def kill_vlc(p_vlc):
    if platform.system() == "Darwin":
        try:
            cpid = psutil.Process(p_vlc.pid).children()[0]
        except IndexError:
            p_vlc = None
            return
        if cpid.name() == gridplayer_path:
            cpid.terminate()
    else:
        p_vlc.terminate()


def get_YN(question: str) -> bool:
    print(f" {question} (Y/N)", flush=True)
    while True:
        response = getch.getch()
        match response.upper():
            case "Y":
                return True
            case "N":
                return False


def get_12APQSZ() -> str:
    print(f"(1 - Delete File 1   2 - Delete File 2   (Z)P-lay   Q-uit   S-kip", flush=True)
    while True:
        response = getch.getch()
        if response.upper() in "12APQSZ":
            return response.upper()


def assemble_name_lists(master: list[ml.Entries], ns: ml.NameSearch):
    """
    Search each entry in master, finding hits against a list of targets.
    Then match that list to a regex, and return the list of indexes to entries that match.
    """
    name_refs = {}
    unlisted_name_refs = {}
    vendors = {}
    for i, item in enumerate(master):
        vendor = ml.get_vendor(item.name)
        if vendor not in vendors.keys():
            vendors[vendor] = []
        vendors[vendor].append(i)
        found_names = ml.search_names(item.name, ns)
        for full_name in found_names:
            if full_name.listed == True:
                if full_name.name not in name_refs.keys():
                    name_refs[full_name.name] = []
                if i not in name_refs[full_name.name]:
                    name_refs[full_name.name].append(i)
            else:
                if full_name.name not in unlisted_name_refs.keys():
                    unlisted_name_refs[full_name.name] = []
                if i not in unlisted_name_refs[full_name.name]:
                    unlisted_name_refs[full_name.name].append(i)
    return name_refs, unlisted_name_refs, vendors


def build_command(*args):
    command = [args[0]]
    if len(args) > 1:
        for i in args[1:]:
            command.append(i)
    return command


def run_viewer(path_1: str, path_2: str, skip_time: int = 0):

    pid = subprocess.Popen(
        build_command(gridplayer_path, path_1, path_2),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return pid


def process_combo(master: list[ml.Entries], i: int, j: int, trigger: int):

    p_vlc = None
    while True:
        if trigger == -2:
            response = "P"
            trigger = 0
        else:
            response = get_12APQSZ()
            if p_vlc:
                # kill_vlc(p_vlc)
                p_vlc.terminate()
                p_vlc = None
        match response:
            case "1":
                ml.move_file(
                    os.path.join(master[i].path, master[i].name),
                    os.path.join(os.path.dirname(master[i].path), "DelLinks"),
                )
                return i
            case "2":
                ml.move_file(
                    os.path.join(master[j].path, master[j].name),
                    os.path.join(os.path.dirname(master[j].path), "DelLinks"),
                )
                return j
            case "A":
                return -2
            case "P" | "Z":
                p_vlc = run_viewer(
                    os.path.join(master[i].path, master[i].name),
                    os.path.join(master[j].path, master[j].name),
                    150,
                )
            case "Q":
                quit()
            case "S":
                return -1


def main():

    args = get_args()

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    response = -1
    master.sort(key=operator.attrgetter("original_duration"))
    name_search = ml.prepare_name_search(args.first_names_file_input_path, args.full_names_file_input_path)
    name_refs, unlisted_name_refs, vendors = assemble_name_lists(master, name_search)
    for name in sorted(name_refs.keys()):
        print(name)
        deleted_list = []
        for (i, j) in itertools.combinations(name_refs[name], 2):
            i_length = master[i].original_duration
            j_length = master[j].original_duration
            if (
                (abs(i_length - j_length) < 10.0)
                and i not in deleted_list
                and j not in deleted_list
                and (ml.get_vendor(master[i].name) == ml.get_vendor(master[j].name))
            ):
                print(f"{master[i].original_size:12d} :: {master[i].original_duration:10f} :: {master[i].name} ")
                print(f"{master[j].original_size:12d} :: {master[j].original_duration:10f} :: {master[j].name} ")
                print()
                response = process_combo(master, i, j, response)
                print()
                if response >= 0:
                    if response not in deleted_list:
                        deleted_list.append(response)


if __name__ == "__main__":
    main()
