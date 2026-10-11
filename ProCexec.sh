#!/bin/bash
# Run Windows .exe submissions from WSL after ProCcompile.sh.
# Usage: bash ProCexec.sh [--stdin=FILE] [BUILD_DIRECTORY]
# Default build directory: ./build; default stdin: /dev/null (EOF).
# With --stdin, every executable receives the entire file independently.
# Executables run in BUILD_DIRECTORY; exec.log/exec.pdf go in the caller's cwd.
# Source and program output are assumed to be UTF-8; nkf is not required.
# exec.log is overwritten. PDF conversion is optional (requires LibreOffice).
# Return status: 0 = success; 1 = run/PDF failure; 2 = setup error.

set -euo pipefail

usage() {
    cat <<'EOS'
Usage: bash ProCexec.sh [--stdin=FILE] [BUILD_DIRECTORY]

  --stdin=FILE   Supply the same input file to every executable.
  --stdin FILE  Equivalent spelling.
  -h, --help    Show this help.
  --            End options (for a directory name beginning with '-').

BUILD_DIRECTORY defaults to build/ in the current directory.
Without --stdin, programs read EOF immediately; no keyboard input is supplied.
exec.log and, if LibreOffice is installed, exec.pdf are saved in the current directory.
EOS
}

die() {
    printf '%s\n' "$1" >&2
    exit 2
}

INPUT=/dev/null
HAS_STDIN=0
BUILDDIR=build
HAS_BUILDDIR=0
OPTIONS=1
while (( $# > 0 )); do
    if (( OPTIONS )); then
        case $1 in
            -h|--help) usage; exit 0 ;;
            --stdin=*)
                (( HAS_STDIN == 0 )) || die 'Specify --stdin only once.'
                INPUT=${1#--stdin=}
                [[ -n $INPUT ]] || die '--stdin requires a file name.'
                HAS_STDIN=1
                shift
                continue
                ;;
            --stdin)
                (( HAS_STDIN == 0 )) || die 'Specify --stdin only once.'
                (( $# >= 2 )) || die '--stdin requires a file name.'
                [[ -n $2 && $2 != --* ]] || die '--stdin requires a file name (use --stdin=FILE for a name beginning with --).'
                INPUT=$2
                HAS_STDIN=1
                shift 2
                continue
                ;;
            --) OPTIONS=0; shift; continue ;;
            -*) die "Unknown option: $1" ;;
        esac
    fi
    (( HAS_BUILDDIR == 0 )) || die 'Specify only one build directory.'
    BUILDDIR=$1
    HAS_BUILDDIR=1
    shift
done

LOGDIR=$(pwd -P)
LOGFILE="$LOGDIR/exec.log"
if (( HAS_STDIN )); then
    [[ -f $INPUT && -r $INPUT ]] || die "Input file not readable: $INPUT"
    INPUT=$(realpath -- "$INPUT")
    # Do not overwrite the input when opening the log (including hard links).
    [[ ! $INPUT -ef $LOGFILE ]] || die 'Input file must not be the output log.'
fi
[[ -d $BUILDDIR ]] || die "Build directory not found: $BUILDDIR"
BUILDDIR=$(cd -- "$BUILDDIR" && pwd -P)

shopt -s nullglob
sources=("$BUILDDIR"/*.c)
(( ${#sources[@]} > 0 )) || die "No .c files found in: $BUILDDIR"

: > "$LOGFILE"
if (( HAS_STDIN )); then
    printf '[Stdin file: %s]\n' "$INPUT" >> "$LOGFILE"
else
    printf '[Stdin: none (EOF)]\n' >> "$LOGFILE"
fi

failed=0
for compc in "${sources[@]}"; do
    name=${compc##*/}
    compexe=${name%.c}.exe
    {
        printf '\n=======%s=======\n' "$name"
        cat -- "$compc"
        printf '\n======================\n[Run %s]\n' "$compexe"
    } >> "$LOGFILE"

    if [[ ! -f "$BUILDDIR/$compexe" ]]; then
        printf 'Skip %s (executable not found)\n' "$compexe" >&2
        printf '[Skipped: executable not found]\n' >> "$LOGFILE"
        failed=1
        continue
    fi

    printf 'Run %s\n' "$compexe"
    status=0
    (cd -- "$BUILDDIR" && "./$compexe" < "$INPUT") >> "$LOGFILE" 2>&1 || status=$?
    printf '\n[Exit status: %s]\n' "$status" >> "$LOGFILE"
    if (( status != 0 )); then
        failed=1
        printf '%s exited with status %s\n' "$compexe" "$status" >&2
    fi
done

printf 'Log: %s\n' "$LOGFILE"
if command -v libreoffice >/dev/null 2>&1; then
    if ! libreoffice --headless \
        --infilter="Text (encoded):UTF8,LF,IPA Gothic,ja-JP" \
        --convert-to pdf --outdir "$LOGDIR" "$LOGFILE"; then
        printf 'PDF conversion failed; the log is available.\n' >&2
        failed=1
    fi
else
    printf 'LibreOffice not found; PDF conversion skipped.\n'
fi
exit "$failed"
