# Media Library Version 23-06-13-a

import bisect
import copy
import csv
import datetime
import hashlib
import operator
import os
import pathlib
import pickle
import shutil
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Tuple

import ffmpeg

# Obsolete entry schema.
# FileEntries = typing.NamedTuple(
#     "FileEntries",
#     [
#         ("path", str),
#         ("name", str),
#         ("original_size", int),
#         ("current_size", int),
#         ("date", datetime.datetime),
#         ("backups", int),
#         ("paths", typing.List),
#         ("original_duration", float),
#         ("current_duration", float),
#         ("ino", int),
#         ("nlink", int),
#         ("csum", str),
#         ("data", typing.Dict),
#     ],
# )


@dataclass
class Entries:
    UID: str = ""
    path: str = ""
    name: str = ""
    original_size: int = 0
    current_size: int = 0
    date: datetime.datetime = datetime.datetime.now()
    backups: int = 0
    paths: list[str] = field(default_factory=list)
    original_duration: float = 0.0
    current_duration: float = 0.0
    ino: int = 0
    nlink: int = 0
    csum: str = ""
    data: dict[Any, Any] = field(default_factory=dict)


@dataclass
class SortPointer:
    key: Any
    index: int = 0


def exit_error(*error_data: Any) -> None:
    for i, data in enumerate(error_data):
        print(data, end=" ")
        if i != len(error_data) - 1:
            print(" : ", end=" ")
    print("")
    sys.exit()


### Physical file operations


def move_file(source: str, target: str, verbose=False, no_action=False) -> os.stat_result:
    if verbose:
        print(f"move_file {source} -> {target}")
    if not no_action:
        try:
            shutil.move(source, target)
        except OSError as e:
            exit_error(f"{source} -> {target} :: File move failed: {e}")
    return os.stat(target)


def copy_file(source: str, target: str, verbose=False, no_action=False) -> os.stat_result:
    if verbose:
        print(f"copy_file {source} -> {target}")
    if not no_action:
        try:
            shutil.copy2(source, target)
        except OSError as e:
            exit_error(f"File copy failed: {e}")
    return os.stat(target)


def checksum(filename: str, hash_factory: Callable[..., Any] = hashlib.md5, chunk_num_blocks: int = 128) -> Any:
    h = hash_factory()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_num_blocks * h.block_size), b""):
            h.update(chunk)
    return h.hexdigest()


def file_duration(filename: str) -> float:
    duration = 0
    try:
        info = ffmpeg.probe(filename)
        duration = info["format"]["duration"]
    except ffmpeg.Error as e:
        print()
        print(e.stderr)
        print()
        return -1
    return float(duration)


### Database operations


def pointer_sort_database(database: list[Entries], sort_key: str = "original_size") -> list[SortPointer]:

    pointers = [SortPointer(getattr(e, sort_key), i) for i, e in enumerate(database)]
    pointers.sort(key=lambda x: getattr(x, "key"))
    return pointers


def deepcopy_sort_database(database: list[Entries], sort_key: str):
    new_db = []
    for i, e in enumerate(database):
        entry = copy.deepcopy(e)
        entry.data["index"] = i
        new_db.append(entry)
    new_db.sort(key=lambda x: getattr(x, sort_key))
    return new_db


def file_md_tag(filename: str) -> Tuple[str, str]:
    # Return tuple of empty strings if tag not found.
    header = "###MDV1###"

    duration = 0
    try:
        info = ffmpeg.probe(filename)
    except ffmpeg.Error as e:
        print()
        print(e.stderr)
        print()
        return ("", "")
    try:
        md_tag = info["format"]["tags"]["comment"]
    except KeyError:
        return ("", "")
    if (header_start := md_tag.find(header)) != 0:
        return ("", "")
    duration, size, *_ = md_tag[header_start + 11 :].split(" ")
    return (duration, size)


# Return True, result if size and name match.
def check_db(database: list[Entries], item: Entries) -> Tuple[bool, int]:
    start = 0
    while True:
        found, result = check_current_size(database, item.current_size, start)
        if found:
            if database[result].name == item.name:
                return True, result
            else:
                start = result
        else:
            return False, 0


def check_inode(database: list[Entries], inode: int) -> Tuple[bool, int]:
    for i, item in enumerate(database):
        if item.ino == inode:
            return (True, i)
    return (False, 0)


def check_inode_in_path(database: list[Entries], path: str, inode: int) -> Tuple[bool, int]:
    for i, item in enumerate(database):
        if (item.ino == inode) and (item.path == path):
            return (True, i)
    return (False, 0)


# Find an entry based on original file size, using a sorted list of pointers to master.
# Return True, resulting master index if size matches.
def check_pointers_to_original_size(
    database: list[Entries], pointers: list[SortPointer], size: int, start: int = 0
) -> Tuple[bool, int]:
    entry_size = operator.attrgetter("size")

    if start > 0:
        result = start + 1
    else:
        result = bisect.bisect_left(pointers, size, key=entry_size)
    if result >= len(pointers) or pointers[result].size != size:
        return (False, 0)
    else:
        return (True, pointers[result].index)


def check_pointers_to_name(master: list[Entries], pointers: list[SortPointer], name: str):
    key = operator.attrgetter("key")

    result = bisect.bisect_left(pointers, name, key=key)
    if result >= len(pointers):
        return (False, "")
    return (True, pointers[result].index)


# Return True, result if size matches.
def check_current_size(database: list[Entries], size: int, start: int = 0) -> Tuple[bool, int]:
    entry_size = operator.attrgetter("current_size")

    if start > 0:
        result = start + 1
    else:
        result = bisect.bisect_left(database, size, key=entry_size)
    if result >= len(database) or database[result].current_size != size:
        return (False, 0)
    else:
        return (True, result)


# Find an entry based on original file size, using a sorted copy of master.
# Return True, result if size matches.
def check_original_size(database: list[Entries], size: int, start: int = 0) -> Tuple[bool, int]:
    entry_size = operator.attrgetter("original_size")

    if start > 0:
        result = start + 1
    else:
        result = bisect.bisect_left(database, size, key=entry_size)
    if result >= len(database) or database[result].original_size != size:
        return (False, 0)
    else:
        return (True, result)


def make_backup_path_entry(path: str, inode: int) -> str:
    processed_path = pathlib.Path(path).expanduser().resolve()
    return processed_path.joinpath(f"[{inode}]").as_posix()


def split_backup_path(path: str) -> Tuple[str, int]:
    split_point = path.find("[")
    end_point = path.find("]")
    return os.path.normpath(path[0:split_point]), int(path[split_point + 1 : end_point])


def create_file_entry(path: str, update_duration: bool = False) -> Entries:
    stat_entry = os.stat(path)
    if update_duration:
        duration = file_duration(path)
    else:
        duration = 0.0
    entry = Entries(
        path=os.path.dirname(path),
        name=os.path.basename(path),
        original_size=stat_entry.st_size,
        current_size=stat_entry.st_size,
        date=datetime.datetime.fromtimestamp(stat_entry.st_mtime, tz=datetime.timezone.utc),
        backups=0,
        paths=[],
        original_duration=duration,
        current_duration=duration,
        ino=stat_entry.st_ino,
        nlink=stat_entry.st_nlink,
        csum="",
        data={},
    )
    return entry


def create_file_list(path: str, update_duration: bool = False) -> list[Entries]:
    entry_size = operator.attrgetter("current_size")
    file_entries: list[Entries] = []
    files = [
        f
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and os.path.splitext(f)[1] in [".mp4", ".mp4~"]
    ]
    for f in files:
        entry = create_file_entry(os.path.join(path, f), update_duration)
        bisect.insort(file_entries, entry, key=entry_size)
    return file_entries


def read_master_file(master_input_path: str) -> list[Entries]:
    master: list[Entries] = []
    if os.path.exists(master_input_path):
        with open(master_input_path, "rb") as f:
            master = pickle.load(f)
        print(f"{len(master)} records found.")
    return master


def write_entries_file(master: list[Entries], master_output_path: str, write_csv: bool) -> None:
    with open(master_output_path, "wb") as f:
        pickle.dump(master, f)

    if write_csv:
        csv_output_path = master_output_path + ".csv"
        with open(csv_output_path, "w") as f:
            w = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            w.writerow(
                [
                    "UID",
                    "Path",
                    "Name",
                    "Ext",
                    "O_Size",
                    "C_Size",
                    "Date",
                    "Backups",
                    "Paths",
                    "O_Duration",
                    "C_Duration",
                    "Ino",
                    "Nlink",
                    "CSum",
                    "Data",
                ]
            )
            w.writerows(
                [
                    item.UID,
                    item.path,
                    item.name,
                    int(item.original_size),
                    int(item.current_size),
                    item.date,
                    int(item.backups),
                    item.paths,
                    float(item.original_duration),
                    float(item.current_duration),
                    int(item.ino),
                    int(item.nlink),
                    item.csum,
                    item.data,
                ]
                for item in master
            )
    print(f"{len(master)} records written.")
