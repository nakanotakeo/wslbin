#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: ${0##*/} file.zip" >&2
    exit 1
fi

zipfile="$1"
exec unzip "$zipfile" -d "${zipfile%.[zZ][iI][pP]}"

