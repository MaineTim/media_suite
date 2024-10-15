import argparse
import os
import re
import time

import ahocorasick_rs as ah

import media_library as ml

import pdb

g_actor_names = []

def get_args():
    parser = argparse.ArgumentParser(description="Search for entries.")
#    parser.add_argument("target_strings", nargs="+")
    parser.add_argument("-m", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-f", type=str, dest="first_names_file_input_path", default="female_first_names.txt")
    parser.add_argument("-i", action="store_true", default=False, dest="case_insensitive", help="Case insensitive.")
    parser.add_argument("-l", type=str, dest="actor_names_file_input_path", default="actor_names.txt")
    parser.add_argument("-p", action="store_true", default=False, dest="print_path", help="Print path.")
    parser.add_argument(
        "-t", action="store_true", default=False, dest="sort_time", help="Sort based on original duration."
    )
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
        if token == "OR" and len(args.target_strings) > i > 0:
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


def word_index(item_name: str, result: tuple[int, int, int]):
    start = result[1]
    end = result[2]
    while (start - 1 > 0) and item_name[start - 1].isalpha():
        start -= 1
    while end < len(item_name) and item_name[end].isalpha():
        end += 1
    return(start, end)


def process_first_name(first_name: str, item_name: str, end: int) -> str:
#    pdb.set_trace()
#    last_name = re.split(r" |,|-", item_name[end:])
#    print(last_name)
    last_name = item_name[end:].split()[0].strip()
    full_name = f"{first_name} {last_name}".strip().title()
    if full_name[-1] is "," or full_name[-1] is "-":
        full_name = full_name[:-1].strip()
    print(full_name)
    if full_name in g_actor_names:
        return full_name
    return ""


def search_names(master, first_names, args):
    """
    Search each entry in master, finding hits against a list of targets.
    Then match that list to a regex, and return the list of indexes to entries that match.
    """
#    target_regex, targets = parse_target_strings(args)
    if args.case_insensitive:
        ah_search = ah.AhoCorasick(list(map(lambda x: x.lower(), first_names)), matchkind=ah.MatchKind.LeftmostLongest)
    else:
        ah_search = ah.AhoCorasick(first_names, matchkind=ah.MatchKind.LeftmostLongest)
    file_indexes = []
    for i, item in enumerate(master):
        if args.case_insensitive:
            results = ah_search.find_matches_as_indexes(item.name.lower())
        else:
            results = ah_search.find_matches_as_indexes(item.name)
        if results != []:
            tokens = ""
            results.sort(key=lambda x: x[0])
            # for x in (list(zip(*results))[0]):
            for result in results:
                start, end = word_index(item.name, result)
                if len(first_names[result[0]]) == end - start:
                    full_name = process_first_name(first_names[result[0]], item.name, end)
                    if full_name is not "":
                        tokens = tokens + full_name + ", "
            print(item.name)
            print(f"Listed: {tokens}")
            print()
    #            if re.search(target_regex, tokens):
#                file_indexes.append(i)
    return file_indexes


def read_first_names_file(name_file_input_path: str) -> list[str]:
    first_names=[]
    if os.path.exists(name_file_input_path):
        with open(name_file_input_path, "r") as f:
            first_names = [name.strip() for name in f]
        print(f"{len(first_names)} records found.")
    return first_names


def read_actor_names_file(actor_names_file_input_path: str) -> list[str]:
    if os.path.exists(actor_names_file_input_path):
        with open(actor_names_file_input_path, "r") as f:
            for name in f:
                g_actor_names.append(name.strip())
        print(f"{len(g_actor_names)} records found.")
    return g_actor_names


def main():
    args = get_args()

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    if (first_names := read_first_names_file(args.first_names_file_input_path)) == []:
        ml.exit_error(f"{args.first_names_file_input_path} not found and is required.")

    if (g_actor_names := read_actor_names_file(args.actor_names_file_input_path)) == []:
        ml.exit_error(f"{args.actor_names_file_input_path} not found and is required.")
 
    search_names(master, first_names, args)


if __name__ == "__main__":
    main()
