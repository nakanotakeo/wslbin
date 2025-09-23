#!/usr/bin/python3 
# strip space, LF etc. to be called from identity_check.sh
import re
import sys

def remove_comments_and_spaces(code):
    # //から行末までのコメントを削除
    code = re.sub(r'//.*', '', code)

    # /* ... */スタイルのコメントを削除
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

    # プリプロセッサディレクティブの改行を維持
    lines = code.split('\n')
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line.startswith('#'):
            lines[i] = stripped_line + '\n'
        else:
            # 不要なスペースを削除
            line = re.sub(r'\s+', ' ', line)  # 連続するスペースを1つのスペースに
            line = re.sub(r'\s*([\(\){};=,])\s*', r'\1', line)  # 演算子や区切り記号の周りのスペースを削除
            lines[i] = line

    return ''.join(lines).strip()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py input_filename.c", file=sys.stderr)
        sys.exit(1)

    input_filename = sys.argv[1]

    with open(input_filename, "r", encoding="utf-8-sig") as f:  # BOM 付きUTF-8として読み込み
        code = f.read()

    cleaned_code = remove_comments_and_spaces(code)

    print(cleaned_code, end='')  # BOMは標準出力のエンコーディングに従って処理される
