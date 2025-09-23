#!/bin/bash

if [ $# -lt 1 ]; then
   echo $0 dir1 dir2 ...
   exit 0
fi

EXDIR=`dirname $0`

CSTRIP=./${EXDIR}/Cstrip.py
WORKDIR=./workdir_identity_check

mkdir -p $WORKDIR
for sdir in "$@"; do
   cp $sdir/*.c $WORKDIR
done

files=($WORKDIR/*.c)
num_files=${#files[@]}

# sompairs all available pairs of files
for ((i=0; i<num_files; i++)); do
    for ((j=i+1; j<num_files; j++)); do
        # compare files with diff command
        if diff -q "${files[$i]}" "${files[$j]}" > /dev/null; then
            echo "${files[$i]} and ${files[$j]} are identical"
        fi
    done
done

for c in $WORKDIR/[^c]*.c; do
   $CSTRIP $c > $WORKDIR/clean_`basename $c`
done;

files=($WORKDIR/clean_*.c)
num_files=${#files[@]}

# compairs all available pairs of stripped files
for ((i=0; i<num_files; i++)); do
    for ((j=i+1; j<num_files; j++)); do
        # compare files with diff command
        if diff -q "${files[$i]}" "${files[$j]}" > /dev/null; then
            echo "${files[$i]} and ${files[$j]} are identical"
        fi
    done
done
