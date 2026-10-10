#!/bin/bash
# Run from WSL after ProCcompile.sh has built Windows .exe files.
# Usage: bash ProCexecStdin.sh [input-file [build-directory]]
# Defaults (relative to the current directory): input.txt, ProCbuild
# Each executable receives the complete input file independently.
# Executables run with the build directory as their working directory.
# UTF-8 source files and program output are assumed; nkf is not required.
# exec.log is overwritten in the current directory on each run.
# If LibreOffice is installed, also convert exec.log to exec.pdf.
# Return status: 0 = successful; 1 = run/PDF failure; 2 = setup error.

set -euo pipefail

if (( $# > 2 )); then
    printf 'Usage: %s [input-file [build-directory]]\n' "$0" >&2
    exit 2
fi

INPUT=${1:-input.txt}
BUILDDIR=${2:-ProCbuild}
LOGDIR=$PWD
LOGFILE="$LOGDIR/exec.log"

if [[ ! -f $INPUT || ! -r $INPUT ]]; then
    printf 'Input file not readable: %s\n' "$INPUT" >&2
    exit 2
fi
if [[ ! -d $BUILDDIR ]]; then
    printf 'Build directory not found: %s\n' "$BUILDDIR" >&2
    exit 2
fi
INPUT=$(realpath -- "$INPUT")
BUILDDIR=$(cd -- "$BUILDDIR" && pwd -P)
if [[ $INPUT == "$LOGFILE" ]]; then
    printf 'Input file must not be the output log.\n' >&2
    exit 2
fi

shopt -s nullglob
sources=("$BUILDDIR"/*.c)
if (( ${#sources[@]} == 0 )); then
    printf 'No .c files found in: %s\n' "$BUILDDIR" >&2
    exit 2
fi

: > "$LOGFILE"
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
    if ! libreoffice --headless --convert-to pdf --outdir "$LOGDIR" "$LOGFILE"; then
        printf 'PDF conversion failed; the log is available.\n' >&2
        failed=1
    fi
else
    printf 'LibreOffice not found; PDF conversion skipped.\n'
fi
exit "$failed"
