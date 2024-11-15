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
    parser.add_argument(
        "-f",
        type=str,
        dest="first_names_file_input_path",
        default="female_first_names.txt",
    )
    parser.add_argument(
        "-i",
        action="store_true",
        default=False,
        dest="case_insensitive",
        help="Case insensitive.",
    )
    parser.add_argument("-l", type=str, dest="full_names_file_input_path", default="full_names.txt")
    parser.add_argument("-p", action="store_true", default=False, dest="print_path", help="Print path.")
    parser.add_argument(
        "-t",
        action="store_true",
        default=False,
        dest="sort_time",
        help="Sort based on original duration.",
    )
    args = parser.parse_args()
    return args


def scan_uderscored_names(master: list[ml.Entries], ns: ml.NameSearch, args):
    """ """
    underscored_listed_names = {}
    underscored_unlisted_names = {}
    for i, item in enumerate(master):
        if "_" in item.name:
            cleaned_item = item.name.replace("_", " ")
            dirty_listed, dirty_unlisted = ml.search_names(item.name, ns, args)
            clean_listed, clean_unlisted = ml.search_names(cleaned_item, ns, args)
            for full_name in clean_listed:
                print(f"{clean_listed} -- {dirty_listed}")
                if full_name not in dirty_listed:
                    if full_name not in underscored_listed_names.keys():
                        underscored_listed_names[full_name] = []
                    if i not in underscored_listed_names[full_name]:
                        underscored_listed_names[full_name].append(i)
            for full_name in clean_unlisted:
                if full_name not in dirty_unlisted:
                    if full_name not in underscored_unlisted_names.keys():
                        underscored_unlisted_names[full_name] = []
                    if i not in underscored_unlisted_names[full_name]:
                        underscored_unlisted_names[full_name].append(i)
    return underscored_listed_names, underscored_unlisted_names


def main():

    args = get_args()

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    name_search = ml.prepare_name_search(args.first_names_file_input_path, args.full_names_file_input_path)

    name_refs, unlisted_name_refs = scan_uderscored_names(master, name_search, args)
    print("Listed:")
    for name in sorted(name_refs.keys()):
        for refs in name_refs[name]:
            print(f"{master[refs].name}")


# print(f"{name}: {len(name_refs[name])}")

#    print("Unlisted:")
#    for name in sorted(unlisted_name_refs.keys()):
#        if len(unlisted_name_refs[name]) >= 1 and " " in name:
#            print(f"{name}: {len(unlisted_name_refs[name])}")


if __name__ == "__main__":
    main()
