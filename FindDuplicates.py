#!/usr/bin/env python3
"""Find duplicate groups in a pool of C files under dirA/build and dirB/build.

Standalone: Python 3.8+, standard library only. See FindDuplicates.md.
Normalization is based on ProCtokens-v1; this is lexical, not semantic equality.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

FORMAT = 'ProCtokens-v1'
SPACE = ' \t\v\f'
PUNCTUATORS = sorted({
    '[', ']', '(', ')', '{', '}', '.', '->', '++', '--', '&', '*', '+',
    '-', '~', '!', '/', '%', '<<', '>>', '<', '>', '<=', '>=', '==', '!=',
    '^', '|', '&&', '||', '?', ':', ';', '...', '=', '*=', '/=', '%=',
    '+=', '-=', '<<=', '>>=', '&=', '^=', '|=', ',', '#', '##',
    '<:', ':>', '<%', '%>', '%:', '%:%:',
}, key=lambda s: (-len(s), s))
UCN = r'(?:\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8})'
IDENT_START = r'(?:[^\W\d]|' + UCN + r')'
IDENT_CONT = r'(?:\w|' + UCN + r')'
IDENT = re.compile(IDENT_START + IDENT_CONT + '*', re.UNICODE)
# Preprocessing numbers: deliberately broader than valid numeric constants.
NUMBER = re.compile(r'(?:[0-9]|\.[0-9])(?:[eEpP][+-]|' + IDENT_CONT + r'|\.)*')
LITERAL = re.compile(r'(?:u8|u|U|L)?["\']')
TRIGRAPH = re.compile(r'\?\?[=()/\'<>!\-]')


class LexError(ValueError):
    """Unsupported or lexically malformed input."""


def _logical_source(source):
    source = source.lstrip('\ufeff')
    source = source.replace('\r\n', '\n').replace('\r', '\n')
    if TRIGRAPH.search(source):
        raise LexError('trigraph detected; this syntax is not supported')
    # Translation phase 2 precedes comment recognition.
    return source.replace('\\\n', '')


def tokenize(source):
    """Return (spelling, preceding_whitespace) tuples; newline is a token.

    Comments become whitespace; block-comment internal newlines are retained.
    Header names in #include are scanned as opaque tokens.
    """
    text = _logical_source(source)
    tokens = []
    i = 0
    gap = False
    line_tokens = []

    def emit(value):
        nonlocal gap
        tokens.append((value, gap))
        if value == '\n':
            line_tokens.clear()
        else:
            line_tokens.append(value)
        gap = False

    def fail(message, offset):
        line = text.count('\n', 0, offset) + 1
        raise LexError('{} (logical line {})'.format(message, line))

    while i < len(text):
        c = text[i]
        if c in SPACE:
            gap = True
            i += 1
            continue
        if c == '\n':
            emit('\n')
            gap = True
            i += 1
            continue
        if text.startswith('//', i):
            end = text.find('\n', i + 2)
            i = len(text) if end < 0 else end
            gap = True
            continue
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0:
                fail('unterminated block comment', i)
            for _ in range(text.count('\n', i, end + 2)):
                emit('\n')
            i = end + 2
            gap = True
            continue

        # In a direct #include, <...> and "..." are header names,
        # not ordinary operators / string literals. Preserve their contents.
        if (len(line_tokens) == 2 and line_tokens[0] in ('#', '%:')
                and line_tokens[1] == 'include' and c in '<"'):
            close = '>' if c == '<' else '"'
            end = text.find(close, i + 1)
            nl = text.find('\n', i + 1)
            if end < 0 or (nl >= 0 and nl < end):
                fail('unterminated include header name', i)
            emit(text[i:end + 1])
            i = end + 1
            continue

        # Check literal prefixes BEFORE identifiers.
        literal = LITERAL.match(text, i)
        if literal:
            start = i
            quote = literal.group()[-1]
            i += len(literal.group())
            while i < len(text):
                if text[i] == '\n':
                    fail('newline in literal', start)
                if text[i] == '\\':
                    i += 2
                elif text[i] == quote:
                    i += 1
                    emit(text[start:i])
                    break
                else:
                    i += 1
            else:
                fail('unterminated literal', start)
            continue
        match = NUMBER.match(text, i) or IDENT.match(text, i)
        if match:
            emit(match.group())
            i = match.end()
            continue
        punct = next((p for p in PUNCTUATORS if text.startswith(p, i)), None)
        if punct is not None:
            emit(punct)
            i += len(punct)
            continue
        fail('unsupported character {!r}'.format(c), i)
    return tokens


def canonical_data(source):
    """Build a versioned JSON-compatible token fingerprint."""
    tokens = tokenize(source)
    items = []
    line = []

    def finish_line():
        if not line:
            return
        values = [value for value, _ in line]
        if values[0] in ('#', '%:'):
            record = {'pp': values}
            if len(values) >= 3 and values[1] == 'define':
                function = len(values) >= 4 and values[3] == '(' and not line[3][1]
                record['macro_kind'] = 'function' if function else 'object'
            items.append(record)
        else:
            items.extend(values)
        line.clear()

    for value, gap in tokens:
        if value == '\n':
            finish_line()
        else:
            line.append((value, gap))
    finish_line()
    return {'format': FORMAT, 'items': items}


def normalize(source):
    """Return compact, deterministic, ASCII JSON without a final newline."""
    return json.dumps(canonical_data(source), ensure_ascii=True, separators=(',', ':'))



def collect_files(parent):
    build = Path(parent) / 'build'
    if not build.is_dir():
        raise ValueError('build directory not found: {}'.format(build))
    # Explicit suffix check also keeps *.C out on case-insensitive platforms.
    return build, sorted((p for p in build.iterdir()
                          if p.suffix == '.c' and p.is_file()), key=lambda p: p.name)


def fingerprint_files(paths, encoding):
    records = []
    failures = 0
    empty = 0
    for path in paths:
        try:
            source = path.read_bytes().decode(encoding)
            data = canonical_data(source)
            if not data['items']:
                print('空・コメントのみのため比較対象外: {}'.format(path), file=sys.stderr)
                empty += 1
                continue
            normalized = json.dumps(data, ensure_ascii=True, separators=(',', ':'))
            digest = hashlib.sha256(normalized.encode('ascii')).digest()
            records.append((path, digest, normalized))
        except (OSError, UnicodeError, LookupError, ValueError) as exc:
            print('解析失敗: {}: {}'.format(path, exc), file=sys.stderr)
            failures += 1
    return records, failures, empty


def matching_groups(records):
    """Group pooled files, comparing normalized data as well as hashes."""
    groups = defaultdict(list)
    for path, digest, normalized in records:
        groups[(digest, normalized)].append(path)
    return [paths for paths in groups.values() if len(paths) >= 2]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='両ディレクトリの build/ 直下の *.c を一つのプールにまとめ、一致グループを検出します。')
    parser.add_argument('dirA', help='第1の親ディレクトリ（build 自体ではありません）')
    parser.add_argument('dirB', help='第2の親ディレクトリ（build 自体ではありません）')
    parser.add_argument('--encoding', default='utf-8-sig',
                        help='両側の入力文字コード（既定: utf-8-sig）')
    parser.add_argument('--tsv', action='store_true',
                        help='一致グループを1ファイル1行の TSV で出力。集計は標準エラー出力へ')
    args = parser.parse_args(argv)
    try:
        import codecs
        codecs.lookup(args.encoding)
        build_a, paths_a = collect_files(args.dirA)
        build_b, paths_b = collect_files(args.dirB)
        if build_a.samefile(build_b):
            raise ValueError('異なる二つの build ディレクトリを指定してください')
    except (OSError, LookupError, ValueError) as exc:
        print('{}: {}'.format(parser.prog, exc), file=sys.stderr)
        return 2

    left, failed_a, empty_a = fingerprint_files(paths_a, args.encoding)
    right, failed_b, empty_b = fingerprint_files(paths_b, args.encoding)
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
    if empty_a or empty_b:
        print('空・コメントのみの除外: A {} / B {}'.format(empty_a, empty_b), file=summary)
    if failed_a or failed_b:
        print('解析失敗: A {} / B {}。上記は解析成功分のみの比較結果です。'.format(
            failed_a, failed_b), file=summary)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
