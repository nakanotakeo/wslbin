#!/usr/bin/env python3
"""C source lexical fingerprints (Python 3.8+, standard library only).

The output is comparison data, NOT compilable C or proof of equivalence.
See ProCtokenize.md for supported syntax and limitations.
"""
import argparse
import hashlib
import json
import re
import sys
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='C source filename, or - for standard input')
    parser.add_argument('-o', '--output', help='output file (UTF-8, LF); default: stdout')
    parser.add_argument('--encoding', default='utf-8-sig', help='input encoding (default: utf-8-sig)')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--pretty', action='store_true', help='indented JSON for inspection')
    mode.add_argument('--hash', action='store_true', help='SHA-256 of compact JSON (without trailing newline)')
    args = parser.parse_args(argv)
    try:
        if args.output and args.input != '-':
            if Path(args.input).resolve() == Path(args.output).resolve():
                raise ValueError('input and output must be different files')
            if Path(args.output).exists() and Path(args.input).samefile(args.output):
                raise ValueError('input and output refer to the same file')
        raw = sys.stdin.buffer.read() if args.input == '-' else Path(args.input).read_bytes()
        source = raw.decode(args.encoding)
        compact = normalize(source)
        if args.hash:
            result = hashlib.sha256(compact.encode('ascii')).hexdigest()
        elif args.pretty:
            result = json.dumps(json.loads(compact), ensure_ascii=True, indent=2)
        else:
            result = compact
        if args.output:
            with open(args.output, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(result + '\n')
        else:
            sys.stdout.write(result + '\n')
        return 0
    except (OSError, UnicodeError, LookupError, ValueError) as exc:
        print('{}: {}'.format(parser.prog, exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
