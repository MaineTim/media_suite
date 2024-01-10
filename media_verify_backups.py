import argparse
import bisect
import getch
import operator
import os

import media_library as ml


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify backup files with no Masterfile entry.")
    parser.add_argument("backup_path", nargs=1)
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-v", action="store_true", default=False, dest="verbose", help="Verbose.")
    args = parser.parse_args()
    return args


def get_reply(question: str) -> bool:
    print(f" {question} (Y/N)", flush=True)
    while True:
        response = getch.getch()
        match response.upper():
            case "Y":
                return True
            case "N":
                return False


def check_master_files(master: list[ml.Entries], curr: ml.Entries) -> int:
    entry_size = operator.attrgetter("current_size")

    result = bisect.bisect_left(master, curr.current_size, key=entry_size)
    while True:
        if result == len(master) or master[result].current_size != curr.current_size:
            return -1
        if master[result].name == curr.name:
            return result
        result += 1


def get_entries_by_duration(master: list[ml.Entries], duration: float) -> list[ml.Entries]:

    entry_list = []
    rdur = round(duration, 1)

    for entry in master:
        if rdur - 0.2 < round(entry.current_duration, 1) < rdur + 0.2:
            entry_list.append(entry)
    return entry_list


def main() -> None:

    args = get_args()
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path
    backup_path = args.backup_path[0]

    if backup_path[-1] != "/":
        backup_path = backup_path + "/"

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")

    if os.path.exists(backup_path):
        working = ml.create_file_list(backup_path)
        print(f"{len(working)} target files loaded.")
    else:
        ml.exit_error(f"{backup_path} doesn't exist!")

    unlink_count = 0
    for item in working:
        result = check_master_files(master, item)
        if result == -1:
            backup_duration = ml.file_duration(os.path.join(item.path, item.name))
            matches = get_entries_by_duration(master, backup_duration)
            print(f"{item.name} - {round(backup_duration, 1)}")
            if matches == []:
                print("No matches found.")
            else:
                for entry in matches:
                    print(f"    {entry.name} - {round(entry.current_duration, 1)}")
            if get_reply("Delete backup file?"):
                os.unlink(os.path.join(item.path, item.name))
                unlink_count += 1
 
    print(f"{unlink_count} files unlinked.")


if __name__ == "__main__":
    main()
