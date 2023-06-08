import argparse
import ast
import csv
import datetime
import os

import media_library as ml
from media_library import Entries

gb_verbose = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert CSV file to master_filelist.")
    parser.add_argument("target_csv", nargs=1)
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv", help="Write CSV.")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    parser.add_argument("-w", action="store_true", default=False, dest="write_file", help="Write master_filelist.")
    args = parser.parse_args()
    return args


def convert_paths(paths_str: str) -> list[str]:
    paths_list = paths_str.split(",")
    paths_list = [path.strip(" ,[]").strip("'") for path in paths_list]
    return paths_list


def main() -> None:
    global gb_verbose

    args = get_args()
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = os.path.splitext(args.target_csv[0])
    gb_verbose = args.verbose

    master = []
    with open(args.target_csv[0], "r") as f:
        r = csv.reader(f)
        next(r)
        for list_item in r:
            item = Entries(*list_item)
            entry = Entries(
                UID=item.UID,
                path=item.path,
                name=item.name,
                original_size=int(item.original_size),
                current_size=int(item.current_size),
                date=datetime.datetime.fromisoformat(item.date),
                backups=int(item.backups),
                paths=convert_paths(item.paths),
                original_duration=float(item.original_duration),
                current_duration=float(item.current_duration),
                ino=int(item.ino),
                nlink=int(item.nlink),
                csum=item.csum,
                data=ast.literal_eval(item.data),
            )
            master.append(entry)

    if args.write_file:
        master.sort(key=lambda x: getattr(x, "current_size"))
        ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
