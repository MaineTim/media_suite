import argparse
import bisect
import operator
import os

import media_library as ml
from media_library import Entries

gb_change_made = False


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete an entry.")
    parser.add_argument(
        "-d", action="store_true", default=False, dest="write_csv", help="Write CSV."
    )
    parser.add_argument("-D", type=str, dest="delete_path", help="Deleted files path.")
    parser.add_argument(
        "--deleted-input-path",
        type=str,
        dest="deleted_input_path",
        default="deleted_filelist",
    )
    parser.add_argument(
        "--deleted-ouput-path", type=str, dest="deleted_output_path", required=False
    )
    parser.add_argument(
        "-i", type=str, dest="master_input_path", default="master_filelist"
    )
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    args = parser.parse_args()
    return args


def remove_backups(entry: ml.Entries) -> None:
    for path in entry.paths:
        path = path[: path.find("[")]
        if os.path.exists(os.path.join(path, entry.name)):
            os.unlink(os.path.join(path, entry.name))
            print(f"Deleting backup {os.path.join(path, entry.name)}")


def remove_file(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    print(f"Unlinking {path}")


def remove_master_entry(master: list[ml.Entries], entry_num: int) -> list[ml.Entries]:
    global gb_change_made

    print(f"Removing entry {master[entry_num].name}")
    del master[entry_num]
    gb_change_made = True
    return master


def process_entry(
    master: list[Entries], item: Entries, deleted_log: list[Entries]
) -> None:

    deleted_entry = None
    found, result = ml.check_inode(master, item.ino)
    if found:
        remove_backups(master[result])
        deleted_entry = master[result]
        master = remove_master_entry(master, result)
    else:
        found, result = ml.check_inode(deleted_log, item.ino)
        if found:
            print(f"{item.name} already logged.")
        else:
            print(f"{item.name} not found in master list.")
    if deleted_entry:
        bisect.insort(
            deleted_log, deleted_entry, key=operator.attrgetter("current_size")
        )
        print(f"Logging {item.name}")
    return (master, deleted_log)


def main() -> None:
    args = get_args()

    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path
    if args.deleted_output_path:
        deleted_output_path = args.deleted_output_path
    else:
        deleted_output_path = args.deleted_input_path

    deleted_log = ml.read_master_file(args.deleted_input_path)

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    if os.path.exists(args.delete_path):
        delete_list = ml.create_file_list(args.delete_path)
        print(f"{len(delete_list)} deleted files loaded.")
    else:
        ml.exit_error(f"{args.delete_path} doesn't exist!")

    for item in delete_list:
        master, deleted_log = process_entry(master, item, deleted_log)

    if gb_change_made:
        ml.write_entries_file(master, master_output_path, args.write_csv)
    ml.write_entries_file(deleted_log, deleted_output_path, args.write_csv)


if __name__ == "__main__":
    main()
