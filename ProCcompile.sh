#!/bin/bash
# Cross-compile Programming C submissions for Windows from WSL.
# Requirements (Debian): sudo apt install gcc-mingw-w64-x86-64
# Usage: bash ProCcompile.sh Cfolder
#
# Copy each Cfolder/*.c to ./build/STUDENT.c without encoding conversion.
# STUDENT is the part before the first underscore, e.g. S227083_us... -> S227083.
# Build ./build/STUDENT.exe with x86_64-w64-mingw32-gcc (Windows binary).
# Compiler stdout/stderr are displayed and saved to ./compile.log (overwritten).
# Each submission must be a standalone UTF-8 C source file.
# Original submissions are not modified. Subdirectories are not searched.
# No execall.sh is generated. Review with ProCexec.sh [--stdin=FILE].
# Matching generated files are overwritten; unrelated old files are left alone.
# Exit status: 0 = all succeeded; 1 = some failed; 2 = setup error.

set -euo pipefail

if (( $# != 1 )); then
    printf 'Usage: %s Cfolder\n' "$0" >&2
    exit 2
fi

COMPILER=x86_64-w64-mingw32-gcc
for tool in "$COMPILER" tee; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required command not found: %s\n' "$tool" >&2
        printf 'Debian compiler installation: sudo apt install gcc-mingw-w64-x86-64\n' >&2
        exit 2
    fi
done

if [[ ! -d $1 ]]; then
    printf 'Source directory not found: %s\n' "$1" >&2
    exit 2
fi
FOLDER=$(cd -- "$1" && pwd -P)
OUTDIR="$PWD/build"
mkdir -p -- "$OUTDIR"
OUTDIR=$(cd -- "$OUTDIR" && pwd -P)
if [[ $FOLDER == "$OUTDIR" ]]; then
    printf 'Source and output directories must be different.\n' >&2
    exit 2
fi

shopt -s nullglob
sources=("$FOLDER"/*.c)
if (( ${#sources[@]} == 0 )); then
    printf 'No .c files found in: %s\n' "$FOLDER" >&2
    exit 2
fi

# Detect name collisions before overwriting generated sources.
declare -A seen=()
for source in "${sources[@]}"; do
    name=${source##*/}
    stem=${name%.c}
    student=${stem%%_*}
    if [[ -z $student ]]; then
        printf 'Cannot derive student ID from: %s\n' "$name" >&2
        exit 2
    fi
    if [[ -n ${seen[$student]+exists} ]]; then
        printf 'Duplicate student ID: %s (%s and %s)\n' "$student" "${seen[$student]}" "$name" >&2
        exit 2
    fi
    seen[$student]=$name
done

# Adjust these arrays to match the options used in class.
# No -std option is imposed: use the installed compiler's default dialect.
CFLAGS=(-Wall -Wextra)
LDLIBS=(-lm)
COMPILE_LOG="$PWD/compile.log"
: > "$COMPILE_LOG"

failed=0
succeeded=0
for source in "${sources[@]}"; do
    name=${source##*/}
    stem=${name%.c}
    student=${stem%%_*}
    compc="$OUTDIR/$student.c"
    executable="$OUTDIR/$student.exe"
    printf '\n[Compile %s -> %s.exe]\n' "$name" "$student" | tee -a "$COMPILE_LOG"
    # Do not allow a failed compile to leave a previous executable for review.
    rm -f -- "$executable"
    if ! cp -- "$source" "$compc"; then
        printf '[Copy failed: %s]\n' "$name" | tee -a "$COMPILE_LOG" >&2
        failed=$((failed + 1))
        continue
    fi
    if "$COMPILER" "${CFLAGS[@]}" "$compc" -o "$executable" "${LDLIBS[@]}" \
        2>&1 | tee -a "$COMPILE_LOG"; then
        succeeded=$((succeeded + 1))
    else
        printf '[Compilation failed: %s]\n' "$name" | tee -a "$COMPILE_LOG" >&2
        failed=$((failed + 1))
    fi
done

printf '\nCompiled: %s; failed: %s\n' "$succeeded" "$failed" | tee -a "$COMPILE_LOG"
printf 'Compiler log: %s\n' "$COMPILE_LOG"
if (( failed > 0 )); then
    exit 1
fi
