#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import defaultdict
from typing import Any


HASH_CHUNK_SIZE = 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only recursive directory scanner and duplicate file detector."
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        help="Directory to scan recursively.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include files and directories whose names start with '.'.",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links while avoiding directory symlink loops.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output a machine-readable JSON report.",
    )
    return parser.parse_args()


def error_record(path: str, operation: str, exc: OSError) -> dict[str, str]:
    return {
        "path": os.path.abspath(path),
        "operation": operation,
        "error": str(exc),
    }


def probe_readable(path: str) -> None:
    """
    Verify that a regular file can actually be opened and read.

    Reading one byte keeps this inexpensive while ensuring files that cannot
    be read are excluded from successful file/byte statistics.
    """
    with open(path, "rb") as handle:
        handle.read(1)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def scan_directory(
    root: str,
    include_hidden: bool,
    follow_symlinks: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    files: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    visited_directories: set[tuple[int, int]] = set()

    def mark_directory_visited(path: str, st: os.stat_result) -> bool:
        if not follow_symlinks:
            return True

        identity = (st.st_dev, st.st_ino)
        if identity in visited_directories:
            return False

        visited_directories.add(identity)
        return True

    def walk(directory: str, directory_stat: os.stat_result) -> None:
        if not mark_directory_visited(directory, directory_stat):
            return

        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda item: item.name)
        except OSError as exc:
            errors.append(error_record(directory, "scandir", exc))
            return

        for entry in entries:
            if not include_hidden and entry.name.startswith("."):
                continue

            entry_path = os.path.abspath(entry.path)

            try:
                is_symlink = entry.is_symlink()
            except OSError as exc:
                errors.append(error_record(entry_path, "is_symlink", exc))
                continue

            if is_symlink and not follow_symlinks:
                continue

            try:
                entry_stat = entry.stat(follow_symlinks=follow_symlinks)
            except OSError as exc:
                errors.append(error_record(entry_path, "stat", exc))
                continue

            mode = entry_stat.st_mode

            if stat.S_ISDIR(mode):
                walk(entry_path, entry_stat)
                continue

            if not stat.S_ISREG(mode):
                continue

            try:
                probe_readable(entry_path)
            except OSError as exc:
                errors.append(error_record(entry_path, "read", exc))
                continue

            files.append(
                {
                    "path": entry_path,
                    "size": entry_stat.st_size,
                    "valid": True,
                }
            )

    try:
        root_stat = os.stat(root, follow_symlinks=True)
    except OSError as exc:
        errors.append(error_record(root, "stat", exc))
        return files, errors

    walk(root, root_stat)
    return files, errors


def find_duplicates(
    files: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for file_info in files:
        if file_info["valid"]:
            by_size[file_info["size"]].append(file_info)

    duplicate_groups: list[dict[str, Any]] = []

    for size in sorted(by_size):
        candidates = by_size[size]

        if len(candidates) < 2:
            continue

        by_hash: dict[str, list[str]] = defaultdict(list)

        for file_info in sorted(candidates, key=lambda item: item["path"]):
            path = file_info["path"]

            try:
                digest = sha256_file(path)
            except OSError as exc:
                file_info["valid"] = False
                errors.append(error_record(path, "sha256", exc))
                continue

            by_hash[digest].append(path)

        for digest, paths in by_hash.items():
            if len(paths) < 2:
                continue

            duplicate_groups.append(
                {
                    "size": size,
                    "sha256": digest,
                    "files": sorted(paths),
                }
            )

    duplicate_groups.sort(
        key=lambda group: (
            group["size"],
            group["files"][0],
        )
    )

    return duplicate_groups


def build_report(
    root: str,
    files: list[dict[str, Any]],
    duplicate_groups: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    valid_files = [file_info for file_info in files if file_info["valid"]]

    sorted_errors = sorted(
        errors,
        key=lambda item: (
            item["path"],
            item["operation"],
            item["error"],
        ),
    )

    return {
        "root": root,
        "file_count": len(valid_files),
        "total_bytes": sum(file_info["size"] for file_info in valid_files),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_groups": duplicate_groups,
        "errors": sorted_errors,
    }


def print_text_report(report: dict[str, Any]) -> None:
    print(f"Root: {report['root']}")
    print(f"Files: {report['file_count']}")
    print(f"Total bytes: {report['total_bytes']}")
    print(f"Duplicate groups: {report['duplicate_group_count']}")
    print(f"Errors: {len(report['errors'])}")

    if report["duplicate_groups"]:
        print()
        print("Duplicates:")

        for index, group in enumerate(report["duplicate_groups"], start=1):
            print()
            print(f"Group {index}:")
            print(f"  Size: {group['size']}")
            print(f"  SHA-256: {group['sha256']}")
            print("  Files:")

            for path in group["files"]:
                print(f"    {path}")

    if report["errors"]:
        print()
        print("Scan errors:")

        for item in report["errors"]:
            print(
                f"  {item['path']} "
                f"[{item['operation']}]: "
                f"{item['error']}"
            )


def validate_root(path: str) -> str:
    root = os.path.abspath(os.path.expanduser(path))

    try:
        root_stat = os.stat(root, follow_symlinks=True)
    except FileNotFoundError:
        raise ValueError(f"PATH does not exist: {root}")
    except NotADirectoryError:
        raise ValueError(f"PATH is not a directory: {root}")
    except OSError as exc:
        raise ValueError(f"Cannot access PATH {root}: {exc}")

    if not stat.S_ISDIR(root_stat.st_mode):
        raise ValueError(f"PATH is not a directory: {root}")

    return root


def main() -> int:
    args = parse_args()

    try:
        root = validate_root(args.path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    files, errors = scan_directory(
        root=root,
        include_hidden=args.include_hidden,
        follow_symlinks=args.follow_symlinks,
    )

    duplicate_groups = find_duplicates(files, errors)

    report = build_report(
        root=root,
        files=files,
        duplicate_groups=duplicate_groups,
        errors=errors,
    )

    if args.json_output:
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=False,
            )
        )
    else:
        print_text_report(report)

    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
