import argparse
import os
import re
import time

import ahocorasick_rs as ah

import media_library as ml

import pdb


def get_args():
    parser = argparse.ArgumentParser(description="Search for entries.")
#    parser.add_argument("target_strings", nargs="+")
    parser.add_argument("-m", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-f", type=str, dest="first_names_file_input_path", default="female_first_names.txt")
    parser.add_argument("-i", action="store_true", default=False, dest="case_insensitive", help="Case insensitive.")
    parser.add_argument("-l", type=str, dest="full_names_file_input_path", default="full_names.txt")
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


def get_full_name(first_name: str, item_name: str, end: int, full_names: list[str], mid_names: list[str]) -> str:
    # if first_name.lower() == "anna": pdb.set_trace()
    element = 1
    name_element = item_name[end:].split()[0].strip()
    last_name = name_element.lower()
    while name_element.title() in mid_names:
        name_element = item_name[end:].split()[element].strip()
        last_name = last_name + " " + name_element
        element += 1
    full_name = f"{first_name} {last_name}".strip().title()
    while full_name[-1] in ",-]_).":
        full_name = full_name[:-1].strip()
    if full_name in full_names:
        return full_name
    return f"###{full_name}"


def get_alias(aliases, full_name:str):
    if full_name in aliases.keys():
        return aliases[full_name]
    return full_name


# def get_names_from_item(item: str):



def search_names(master: list[ml.Entries], ns: ml.NameSearch, args):
    """
    Search each entry in master, finding hits against a list of targets.
    Then match that list to a regex, and return the list of indexes to entries that match.
    """
#    target_regex, targets = parse_target_strings(args)
    name_refs = {}
    unlisted_name_refs = {}
    for i, item in enumerate(master):
        if args.case_insensitive:
            results = ns.ah_search.find_matches_as_indexes(item.name.lower())
        else:
            results = ns.ah_search.find_matches_as_indexes(item.name)
        if results != []:
            results.sort(key=lambda x: x[0])
            for result in results:
                start, end = word_index(item.name, result)
                if len(ns.first_names[result[0]]) == end - start:
                    full_name = get_full_name(ns.first_names[result[0]], item.name, end, ns.full_names, ns.mid_names)
                    if full_name[0:3] != "###":
                        full_name = get_alias(ns.aliases, full_name)
                        if full_name not in name_refs.keys():
                            name_refs[full_name] = []
                        if i not in name_refs[full_name]:  
                            name_refs[full_name].append(i)
                    else:
                        full_name = full_name[3:]
                        full_name = get_alias(ns.aliases, full_name)
                        if full_name not in unlisted_name_refs.keys():
                            unlisted_name_refs[full_name] = []
                        if i not in unlisted_name_refs[full_name]:
                            unlisted_name_refs[full_name].append(i)
    return name_refs, unlisted_name_refs


def prepare_name_search(first_names_file_input_path: str, full_names_file_input_path: str, case_insensitive: bool = True):
    """ 
    Load the first_name and full_name files, adding any first names from full_names to first_names.
    Add any alternate names to aliases dict.
    Create the search object.
    """
    def read_first_names_file(first_names_file_input_path: str) -> list[str]:
        first_names=[]
        if os.path.exists(first_names_file_input_path):
            with open(first_names_file_input_path, "r") as f:
                first_names = [name.strip().title() for name in f]
            print(f"{len(first_names)} records found.")
        else:
            ml.exit_error(f"{args.first_names_file_input_path} not found and is required.")
        return first_names

    def read_full_names_file(full_names_file_input_path: str) -> list[str]:
        full_names = []
        aliases = {}
        mid_names = ["De", "Del", "La", "St", "Von", ]
        if os.path.exists(full_names_file_input_path):
            with open(full_names_file_input_path, "r") as f:
                for name in f:
                    if (x := name.find("-->")) != -1:
                        alias = name[x+3:].strip().title()
                        name = name[:x].strip().title()
                        aliases[name] = alias
                    full_names.append(name.strip().title())
                    split_name = full_names[-1].split()
                    if (length:= len(split_name)) > 2:
                        for count in range(1, length - 1):
                            if split_name[count] not in mid_names:
                                mid_names.append(split_name[count])
            print(f"{len(full_names)} records found.")
        else:
            ml.exit_error(f"{args.first_names_file_input_path} not found and is required.")
        return full_names, aliases, mid_names

    ns = ml.NameSearch()
    ns.first_names = read_first_names_file(first_names_file_input_path)
    ns.full_names, ns.aliases, ns.mid_names = read_full_names_file(full_names_file_input_path)
    # Check through the first names in full_names and make sure they in the first_name list.
    full_first_names = (name.split()[0] for name in ns.full_names)   
    for first_name in full_first_names:
        if first_name not in ns.first_names:
            ns.first_names.append(first_name)
    sorted(ns.first_names)
    if case_insensitive:
        ns.ah_search = ah.AhoCorasick(list(map(lambda x: x.lower(), ns.first_names)), matchkind=ah.MatchKind.LeftmostLongest)
    else:
        ns.ah_search = ah.AhoCorasick(ns.first_names, matchkind=ah.MatchKind.LeftmostLongest)
 
    return(ns)


def main():

    args = get_args()

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    name_search = prepare_name_search(args.first_names_file_input_path, args.full_names_file_input_path)

    # pdb.set_trace()

    name_refs, unlisted_name_refs = search_names(master, name_search, args)
    print("Listed:")
    for name in sorted(name_refs.keys()):
        print(f"{name}: {len(name_refs[name])}")
    print("Unlisted:")
    for name in sorted(unlisted_name_refs.keys()):
        if len(unlisted_name_refs[name]) >= 1 and " " in name:
            print(f"{name}: {len(unlisted_name_refs[name])}")


if __name__ == "__main__":
    main()
