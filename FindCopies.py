#!/usr/bin/env python3
"""Find groups of byte-identical C files in dirA/build and dirB/build.

Standalone: Python 3.8+, standard library only. See FindCopies.md.
No decoding, tokenization, whitespace removal, or newline conversion.
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


def collect_files(parent):
    build = Path(parent) / 'build'
    if not build.is_dir():
        raise ValueError('build directory not found: {}'.format(build))
    # Explicit suffix check also keeps *.C out on case-insensitive platforms.
    return build, sorted((p for p in build.iterdir()
                          if p.suffix == '.c' and p.is_file()), key=lambda p: p.name)


def fingerprint_files(paths):
    records = []
    failures = 0
    for path in paths:
        try:
            data = path.read_bytes()
            digest = hashlib.sha256(data).digest()
            records.append((path, digest, data))
        except OSError as exc:
            print('読込み失敗: {}: {}'.format(path, exc), file=sys.stderr)
            failures += 1
    return records, failures


def matching_groups(records):
    """Group pooled files by exact bytes as well as hashes."""
    groups = defaultdict(list)
    for path, digest, data in records:
        groups[(digest, data)].append(path)
    return [paths for paths in groups.values() if len(paths) >= 2]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='両ディレクトリの build/ 直下の *.c を一つのプールにまとめ、バイト列の完全一致を検出します。')
    parser.add_argument('dirA', help='第1の親ディレクトリ（build 自体ではありません）')
    parser.add_argument('dirB', help='第2の親ディレクトリ（build 自体ではありません）')
    parser.add_argument('--tsv', action='store_true',
                        help='一致グループを1ファイル1行の TSV で出力。集計は標準エラー出力へ')
    args = parser.parse_args(argv)
    try:
        build_a, paths_a = collect_files(args.dirA)
        build_b, paths_b = collect_files(args.dirB)
        if build_a.samefile(build_b):
            raise ValueError('異なる二つの build ディレクトリを指定してください')
    except (OSError, ValueError) as exc:
        print('{}: {}'.format(parser.prog, exc), file=sys.stderr)
        return 2

    left, failed_a = fingerprint_files(paths_a)
    right, failed_b = fingerprint_files(paths_b)
    if not paths_a:
        print('注意: .c ファイルがありません: {}'.format(build_a), file=sys.stderr)
    if not paths_b:
        print('注意: .c ファイルがありません: {}'.format(build_b), file=sys.stderr)
    groups = matching_groups(left + right)
    writer = None
    if args.tsv:
        writer = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
        writer.writerow(['group_id', 'group_size', 'member_index', 'file'])
    matched_count = 0
    for group_id, paths in enumerate(groups, 1):
        matched_count += len(paths)
        if not writer:
            print('一致 {}:'.format(len(paths)))
        for member_index, path in enumerate(paths, 1):
            if writer:
                writer.writerow([group_id, len(paths), member_index, str(path)])
            else:
                display = str(path)
                if any(c in display for c in '\r\n\t'):
                    display = json.dumps(display, ensure_ascii=False)
                print('   {}: {}'.format(member_index, display))
        if not writer:
            print()
    summary = sys.stderr if args.tsv else sys.stdout
    print('比較対象: 計 {} ファイル（A {} / B {}）'.format(
        len(left) + len(right), len(left), len(right)), file=summary)
    print('一致: {} グループ / {} ファイル'.format(len(groups), matched_count), file=summary)
    if failed_a or failed_b:
        print('読込み失敗: A {} / B {}。上記は読込み成功分のみの比較結果です。'.format(
            failed_a, failed_b), file=summary)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
