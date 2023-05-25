import argparse
import os
import sys

import media_library as ml

gb_no_action = False
gb_verbose = False


def exit_error(*error_data):
    for i, data in enumerate(error_data):
        print(data, end=" ")
        if i != len(error_data) - 1:
            print(" : ", end=" ")
    print("")
    sys.exit()


def get_args():
    parser = argparse.ArgumentParser(description="Delete deleted backup files.")
    parser.add_argument("target_path", nargs=1)
    parser.add_argument("-d", action="store_true", default=False, dest="write_csv")
    parser.add_argument("-D", type=str, dest="delete_path")
    parser.add_argument("--deleted-input-path", type=str, dest="deleted_input_path", default="deleted_filelist")
    parser.add_argument("--deleted-ouput-path", type=str, dest="deleted_output_path", required=False)
    parser.add_argument("-i", type=str, dest="master_input_path", default="master_filelist")
    parser.add_argument("-n", action="store_true", default=False, dest="no_action")
    parser.add_argument("-o", type=str, dest="master_output_path", required=False)
    parser.add_argument("-u", action="store_true", default=False, dest="update_duration")
    parser.add_argument("-v", action="store_true", default=False, dest="verbose")
    args = parser.parse_args()
    return args


def find_inode(target_list, inode):
    for item in target_list:
        if item.ino == inode:
            return (1, item.name)
    return (0, "")


def remove_file(path):
    if gb_verbose:
        print(f"Deleting {path}")
    if not gb_no_action:
        try:
            os.unlink(path)
        except FileNotFoundError:
            return


def main():
    global gb_no_action
    global gb_verbose

    args = get_args()

    gb_verbose = args.verbose
    gb_no_action = args.no_action

    if args.master_output_path:
        master_output_path = args.master_output_path
    else:
        master_output_path = args.master_input_path
    if args.deleted_output_path:
        deleted_output_path = args.deleted_output_path
    else:
        deleted_output_path = args.deleted_input_path
    target_path = args.target_path[0]

    if (deleted := ml.read_master_file(args.deleted_input_path)) == []:
        exit_error(f"{args.deleted_input_path} not found and is required.")
    if (master := ml.read_master_file(args.master_input_path)) == []:
        exit_error(f"{args.master_input_path} not found and is required.")
    print(f"{len(master)} master records loaded.")
    print(f"{len(deleted)} deleted records loaded.")

    if os.path.exists(target_path):
        target_list = ml.create_file_list(target_path)
        print(f"{len(target_list)} target files loaded.")
    else:
        exit_error(f"{target_path} doesn't exist!")

    for item in deleted[:]:
        for i, whole_path in enumerate(item.paths):
            path, inode = ml.split_backup_path(whole_path)
            backup_path = os.path.join(path, item.name)
            if os.path.exists(path):
                if os.path.exists(backup_path):
                    # Found a matching name, if inode okay, then remove it.
                    if gb_verbose:
                        print(f"Found matching filename {backup_path}")
                    backup_stat = os.stat(backup_path)
                    if int(backup_stat.st_ino) == inode:
                        remove_file(backup_path)
                    else:
                        if gb_verbose:
                            print(f"Inodes don't match! {backup_stat.st_ino} {inode}")
                    deleted.remove(item)
                else:
                    found, filename = find_inode(target_list, inode)
                    if found:
                        # Found the inode entry file, if duration matches entry, remove it.
                        if gb_verbose:
                            print(f"Found matching inode {inode} {item.name}: {filename}")
                        if ml.file_duration(os.path.join(target_path, filename)) == item.current_duration:
                            remove_file(os.path.join(target_path, filename))
                        else:
                            if gb_verbose:
                                print(
                                    f"Durations don't match! {ml.file_duration(os.path.join(target_path, filename))} {item.current_duration}"
                                )
                        deleted.remove(item)
                    else:
                        if gb_verbose:
                            print(f"No backup found: {backup_path}")
    ml.write_entries_file(deleted, deleted_output_path, True)


if __name__ == "__main__":
    main()
