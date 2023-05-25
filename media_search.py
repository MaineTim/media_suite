import argparse
import os
import re
import sys
import time

import ahocorasick_rs as ah

import media_library as ml


def exit_error(*error_data):
    for i, data in enumerate(error_data):
        print(data, end=" ")
        if i != len(error_data) - 1:
            print(" : ", end=" ")
    print("")
    sys.exit()


def get_args():
    parser = argparse.ArgumentParser(description="Search for entries.")
    parser.add_argument("target_strings", nargs="+")
    parser.add_argument("-m", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-i", action="store_true", default=False, dest="case_insensitive")
    parser.add_argument("-p", action="store_true", default=False, dest="print_path")
    parser.add_argument("-t", action="store_true", default=False, dest="sort_time")
    args = parser.parse_args()
    return args


def parse_target_strings(args):
    """
    Create a regex that will match the set of targets given.
    "OR" is the only boolean implemented.
    """
    target_regex = ""
    targets = []
    or_count = 0
    i = -1
    for token in args.target_strings:
        i += 1
        if token == "OR" and i > 0 and len(args.target_strings) > i:
            if or_count < 1:
                target_regex = target_regex[: len(target_regex) - 1] + "[" + target_regex[len(target_regex) - 1 :]
            or_count = 2
            i -= 1
        else:
            if or_count == 1:
                target_regex += "]"
            target_regex += str(i)
            targets.append(token)
            or_count -= 1
    if or_count > 0:
        target_regex += "]"
    return target_regex, targets


def search_strings(master, args):
    """
    Search each entry in master, finding hits against a list of targets.
    Then match that list to a regex, and return the list of indexes to entries that match.
    """
    target_regex, targets = parse_target_strings(args)
    if args.case_insensitive:
        ah_search = ah.AhoCorasick(list(map(lambda x: x.upper(), targets)))
    else:
        ah_search = ah.AhoCorasick(targets)
    file_indexes = []
    for i, item in enumerate(master):
        if args.case_insensitive:
            results = ah_search.find_matches_as_indexes(item.name.upper())
        else:
            results = ah_search.find_matches_as_indexes(item.name)
        if results != []:
            results.sort(key=lambda x: x[0])
            tokens = "".join([str(x) for x in (list(zip(*results))[0])])
            if re.search(target_regex, tokens):
                file_indexes.append(i)
    return file_indexes


def main():
    args = get_args()

    if (master := ml.read_master_file(args.master_input_path)) == []:
        exit_error(f"{args.master_input_path} not found and is required.")

    results = search_strings(master, args)
    entries = [master[res] for res in results]
    if args.sort_time:
        entries.sort(key=lambda x: float(x.original_duration))
    else:
        entries.sort(key=lambda x: x.name)
    if args.print_path:
        [
            print(
                f'{time.strftime("%H:%M:%S", time.gmtime(float(ent.original_duration)))} - {os.path.join(ent.path, ent.name)}'
            )
            for ent in entries
        ]
    else:
        [
            print(f'{time.strftime("%H:%M:%S", time.gmtime(float(ent.original_duration)))} - {ent.name}')
            for ent in entries
        ]


if __name__ == "__main__":
    main()
