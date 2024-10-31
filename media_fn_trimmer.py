import argparse
import bisect
import operator
import os
import shutil
import typing

import media_library as ml

FileEntries = typing.NamedTuple("FileEntries", [("name", str), ("size", int)])

gb_no_action = False
gb_trim_number = False
gb_verbose = False


def get_args():
    parser = argparse.ArgumentParser(description="Trim filenames of target phrase.")
    parser.add_argument("target_phrase", nargs=1)
    parser.add_argument("target_path", nargs=1)
    parser.add_argument("-i", action="store_true", default=False, dest="add_index", help="Add index number.")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument("-t", action="store_true", default=False, dest="trim_number", help="Trim numbers.")
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose")
    args = parser.parse_args()
    return args


def rename_file(target_path, orig, name):
    if gb_verbose:
        print(f"Moving {os.path.join(target_path, orig.name)} -> {name}\n")
    if not gb_no_action:
        if os.path.exists(os.path.join(target_path, name)):
            ml.exit_error(f"{os.path.join(target_path, name)} already exists")
        shutil.move(os.path.join(target_path, orig.name), os.path.join(target_path, name))


def create_file_list(path):
    entry_size = operator.attrgetter("size")
    file_entries = []
    files = [
        f
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and os.path.splitext(f)[1] in [".mp4", ".mp4~"]
    ]
    for f in files:
        entry_path = os.path.join(path, f)
        entry = FileEntries(name=f, size=os.stat(entry_path).st_size)
        bisect.insort(file_entries, entry, key=entry_size)
    return file_entries


def find_phrase(item, phrase, anchor):
    p_index = -1
    beginning = 0
    iter_item = iter(item)
    # Keep resetting p_index and beginning until we hit the phrase.
    for l_index, letter in enumerate(iter_item):
        p_index += 1
        # Anchor check (ie ".mp4").
        if letter == "." and beginning != 0:
            if item[l_index:] == anchor:
                return beginning
        # Numerical extension check (ie "-1").
        if p_index > len(phrase) - 1:
            if not gb_trim_number:
                return -1
            if letter in "0123456789-":
                continue
        # Phrase element check.
        elif letter == phrase[p_index]:
            if beginning == 0:
                beginning = l_index
        else:
            beginning = 0
            p_index = -1
    return -1


def add_numeric_index(name: str, index: int):

    index += 1
    loc = name.rfind(" - ")
    if loc == -1:
        loc = len(name) - 1
    return (index, name[:loc] + f" {index:03}" + name[loc:])


def main():
    global gb_no_action
    global gb_trim_number
    global gb_verbose

    args = get_args()
    target_path = args.target_path[0]
    gb_verbose = args.verbose
    gb_no_action = args.no_action
    gb_trim_number = args.trim_number
    index = 0

    target = create_file_list(target_path)

    for item in target:
        if (ind := find_phrase(item.name, args.target_phrase[0], ".mp4")) != -1:
            new_name = item.name[:ind] + ".mp4"
            if args.add_index:
                index, new_name = add_numeric_index(new_name, index)
            rename_file(target_path, item, new_name)


if __name__ == "__main__":
    main()
