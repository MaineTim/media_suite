import argparse
import datetime
import os

import getch

import media_library as ml


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the database.")
    parser.add_argument("backup_path", nargs=1)
    parser.add_argument(
        "-d",
        action="store_true",
        default=False,
        dest="write_csv",
        help="Write CSV file.",
    )
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action", help="No action.")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument(
        "-w",
        action="store_true",
        default=False,
        dest="write_file",
        help="Write master_filelist.",
    )
    args = parser.parse_args()
    return args


def main() -> None:
    args = get_args()
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path

    backup_path = args.backup_path[0]
    if backup_path[-1] != "/":
        backup_path = backup_path + "/"
    backup_path = backup_path + "Spank"

    changed = False

    if (master := ml.read_master_file(args.master_input_path)) == []:
        ml.exit_error(f"{args.master_input_path} not found and is required.")
        
    for i, item in enumerate(master):
        for j, whole_path in enumerate(item.paths[:]):
            path, _ = ml.split_backup_path(whole_path)
            source_path = os.path.join(item.path, item.name)
            target_path = os.path.join(path, item.name)
            if path == backup_path and os.path.exists(source_path) and not os.path.exists(target_path): 
                ml.copy_file(source_path, target_path, True, args.no_action)
                if not args.no_action:
                    target_stat = os.stat(target_path)
                    target_entry = ml.make_backup_path_entry(path, target_stat.st_ino)
                    master[i].paths[j] = target_entry
                    changed = True

    if changed and args.write_file:
        master.sort(key=lambda x: getattr(x, "current_size"))
        ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
