import argparse
import datetime
import os

import getch

import media_library as ml


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the database.")
    parser.add_argument("-c", action="store_true", default=False, dest="check_types", help="Check types.")
    parser.add_argument("-C", action="store_true", default=False, dest="clear_data", help="Clear data field.")
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv", help="Write CSV file.")
    parser.add_argument("-D", action="store_true", default=False, dest="dump_data", help="Dump data field.")
    parser.add_argument("-f", action="store_true", default=False, dest="fix_errors", help="Fix errors.")
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument(
        "-s",
        action="store_true",
        default=False,
        dest="suppress_backup_warning",
        help="Suppress no valid backup warning.",
    )
    parser.add_argument("-w", action="store_true", default=False, dest="write_file", help="Write master_filelist.")
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


def normalize_paths(paths: list[str]) -> list[str]:
    normpath = []
    for whole_path in paths[:]:
        path, inode = ml.split_backup_path(whole_path)
        normpath.append(ml.make_backup_path_entry(path, inode))
    return normpath


def main() -> None:
    args = get_args()
    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path

    changed = False

    if (master := ml.read_master_file(args.master_input_path)) != []:

        if args.check_types:
            for i in range(len(master)):
                try:
                    if not isinstance(master[i].UID, str):
                        master[i].UID = str(master[i].UID)
                        changed = True
                    if not isinstance(master[i].path, str):
                        master[i].path = str(master[i].path)
                        changed = True
                    if not isinstance(master[i].name, str):
                        master[i].name = str(master[i].name)
                        changed = True
                    if not isinstance(master[i].original_size, int):
                        master[i].original_size = int(master[i].original_size)
                        changed = True
                    if not isinstance(master[i].current_size, int):
                        master[i].current_size = int(master[i].current_size)
                        changed = True
                    if not isinstance(master[i].backups, int):
                        master[i].backups = int(master[i].backups)
                        changed = True
                    if not isinstance(master[i].original_duration, float):
                        master[i].original_duration = float(master[i].original_duration)
                        changed = True
                    if not isinstance(master[i].current_duration, float):
                        master[i].current_duration = float(master[i].current_duration)
                        changed = True
                    if not isinstance(master[i].ino, int):
                        master[i].ino = int(master[i].ino)
                        changed = True
                    if not isinstance(master[i].nlink, int):
                        master[i].nlink = int(master[i].nlink)
                        changed = True
                    if not isinstance(master[i].csum, str):
                        master[i].csum = str(master[i].csum)
                        changed = True
                except (ValueError, TypeError) as e:
                    ml.exit_error(e)
                if not isinstance(master[i].date, datetime.datetime):
                    ml.exit_error(f"{master[i].name} date field is invalid: {master[i].date}")
                if not isinstance(master[i].data, dict):
                    ml.exit_error(f"{master[i].name} data field is invalid: {master[i].data}")

        # Create a list of inodes, and check that there are no duplicates (multiple entries pointing to one file).
        inodes = sorted([(i, item.ino) for i, item in enumerate(master)], key=lambda x: x[1])
        for i in range(len(inodes) - 1):
            if inodes[i][1] == inodes[i + 1][1] and master[inodes[i][0]].path == master[inodes[i + 1][0]].path:
                item_a = os.path.join(master[inodes[i][0]].path, master[inodes[i][0]].name)
                item_b = os.path.join(master[inodes[i + 1][0]].path, master[inodes[i + 1][0]].name)
                print(f"{item_a}")
                print(f"{item_b} inodes match.")

        for i, item in enumerate(master):
            target_path = os.path.join(item.path, item.name)

            # Check is there's a valid file with the entry name.
            # If not, flag it.
            if os.path.exists(target_path):
                target_stat = os.stat(target_path)
            else:
                print(f"{target_path} doesn't exist!")
                continue
            # Entry doesn't match target inode, flag it.
            if target_stat.st_ino != item.ino:
                print(f"{target_path} inode {target_stat.st_ino} doesn't match entry {item.ino}.")
                if args.fix_errors:
                    if get_reply("Fix this error?"):
                        master[i].ino = target_stat.st_ino
                        changed = True
                continue
            # Entry size doesn't match, flag it.
            if target_stat.st_size != item.current_size:
                print(f"{target_path} has changed size from {item.current_size} to {target_stat.st_size}.")
                continue

            if (normal_paths := normalize_paths(item.paths)) != item.paths:
                paths = list(set(normal_paths))
                print(f"Paths corrected: {item.paths} -> {paths}")
                master[i].paths = paths
                master[i].backups = len(paths)
                item.paths = paths
                item.backups = len(paths)
                changed = True

            if len(item.paths) != item.backups:
                print(f"{target_path} backup count {item.backups} does not match path list length {len(item.paths)}.")
                if args.fix_errors:
                    if get_reply("Fix this error?"):
                        master[i].backups = len(item.paths)
                        changed = True

            for j, whole_path in enumerate(item.paths[:]):
                if item.paths.count(whole_path) > 1:
                    print(f"Multiple entries for {item.name}: {whole_path}")
                    if args.fix_errors:
                        if get_reply("Fix this error?"):
                            del master[i].paths[j]
                            master[i].backups -= 1
                            changed = True
                else:
                    path, inode = ml.split_backup_path(whole_path)
                    backup_path = os.path.join(path, item.name)
                    if os.path.exists(path):
                        if os.path.exists(backup_path):
                            backup_stat = os.stat(backup_path)
                            # Backup inode doesn't match.
                            if backup_stat.st_ino != inode:
                                print(f"{backup_path} backup inode {backup_stat.st_ino} doesn't match entry {inode}.")
                                if args.fix_errors:
                                    if get_reply("Fix this error?"):
                                        master[i].paths[j] = f"{path}/[{backup_stat.st_ino}]"
                                        changed = True
                                continue
                            # Backup size doesn't match.
                            if backup_stat.st_size != item.original_size:
                                print(
                                    f"{backup_path} backup has changed size from {item.original_size} to {backup_stat.st_size}."
                                )
                                continue
                        else:
                            print(f"{backup_path} backup doesn't exist. {item.backups} backups listed.")
                            if args.fix_errors:
                                master[i].paths.remove(whole_path)
                                master[i].backups -= 1
                                changed = True
                            continue
            if master[i].backups < 1 and len(master[i].paths) < 1:
                if not args.suppress_backup_warning:
                    print(f"Warning: {target_path} has no valid backups.")

        print(f"{len(master)} records checked.")

        if args.dump_data:
            for i, _ in enumerate(master):
                if master[i].data != {}:
                    print(f"{master[i].data}")

        if args.clear_data:
            for item in master:
                item.data = {}
            changed = True

        if changed and args.write_file:
            master.sort(key=lambda x: getattr(x, "current_size"))
            ml.write_entries_file(master, master_output_path, args.write_csv)


if __name__ == "__main__":
    main()
