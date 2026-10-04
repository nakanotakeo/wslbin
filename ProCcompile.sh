#!/bin/bash
# Compile Programming C submissions with GCC on WSL/Linux.
# Requirements (Debian): sudo apt install gcc
# Usage: bash ProCcompile_gcc.sh Cfolder
#
# Each Cfolder/usXXXXXX_Name.c is copied to ProCbuild/usXXXXXX.c,
# then compiled to ProCbuild/usXXXXXX.out. The part before the first
# underscore is used as the student ID (e.g. S227083_us227083_... -> S227083).
# Encoding and line endings are preserved; UTF-8 source files are assumed.
# Files directly inside Cfolder are processed; subdirectories are not searched.
# Each submission must be a standalone C source file using standard C libraries.
# Original submissions are never modified.
# Run the generated checker separately: bash ProCbuild/execall.sh
# Compiler log: bash ProCcompile_gcc.sh Cfolder > Compile.log 2>&1
# Run log: bash ProCbuild/execall.sh | tee ExecAll.log
# Existing generated files with matching names are overwritten on each run.
# Return status: 0 = all compiled; 1 = at least one failed; 2 = setup error.

set -euo pipefail

if (( $# != 1 )); then
    printf 'Usage: %s Cfolder\n' "$0" >&2
    exit 2
fi

for tool in gcc; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required command not found: %s (Debian: sudo apt install gcc)\n' "$tool" >&2
        exit 2
    fi
done

if [[ ! -d $1 ]]; then
    printf 'Source directory not found: %s\n' "$1" >&2
    exit 2
fi
FOLDER=$(cd -- "$1" && pwd -P)
OUTDIR="$PWD/ProCbuild"
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

# Check all derived names before overwriting any generated source files.
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

# Edit these arrays to match the compiler options used in class.
# No -std option is imposed: GCC uses its default language dialect.
CFLAGS=(-Wall -Wextra)
LDLIBS=(-lm)

runner="$OUTDIR/execall.sh"
cat > "$runner" <<'EOS'
#!/bin/bash
# Generated checker. Only successfully compiled submissions are included.
set -u
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1

check_one() {
    local source=$1 executable=$2 original=$3 status
    printf '\n[List %s (submitted as %s)]\n' "$source" "$original"
    cat -- "$source"
    printf '\n[Exec %s]\n' "$executable"
    read -r -p 'Press Enter to run (Ctrl-C to stop): ' || exit 1
    "./$executable"
    status=$?
    printf '\n[Exit status: %s]\n' "$status"
}
EOS

failed=0
succeeded=0
for source in "${sources[@]}"; do
    name=${source##*/}
    stem=${name%.c}
    student=${stem%%_*}
    compc="$OUTDIR/$student.c"
    executable="$OUTDIR/$student.out"
    printf '\n[Compile %s -> %s.out]\n' "$name" "$student"
    # Remove a previous executable so a failed compile cannot run stale code.
    rm -f -- "$executable"
    if ! cp -- "$source" "$compc"; then
        printf '[Copy failed: %s]\n' "$name" >&2
        failed=$((failed + 1))
        continue
    fi
    if gcc "${CFLAGS[@]}" "$compc" -o "$executable" "${LDLIBS[@]}"; then
        printf 'check_one %q %q %q\n' "$student.c" "$student.out" "$name" >> "$runner"
        succeeded=$((succeeded + 1))
    else
        printf '[Compilation failed: %s]\n' "$name" >&2
        failed=$((failed + 1))
    fi
done

chmod +x -- "$runner"
printf '\nCompiled: %s; failed: %s\n' "$succeeded" "$failed"
printf 'To review submissions: bash %q\n' "$runner"
if (( failed > 0 )); then
    exit 1
fi
