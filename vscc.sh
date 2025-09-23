#!/bin/bash
#
# Run from WSL shell. nkf is required. Visual Studio 2022 Community should also be installed.
# usXXXXXX_TheirName.c is assumed at the subdirectory to be given as a command line option.
# You can log the output of cl.exe by redirecting the command | nkf -w > foo.log
#
if [ $# -ne 1 ]; then
  echo "Usage: $0 [c src]";
  exit 1
fi
SRC=$1

COMPC=`basename $SRC | cut -d _ -f 1`_target.c
nkf -Lw --oc=UTF-8-BOM "$SRC" > $COMPC

TMPBAT=temp_$$.bat
cat << 'EOS' > ./$TMPBAT
chcp 65001
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
EOS
echo -n "cl.exe $COMPC" >> $TMPBAT

cmd.exe /c $TMPBAT

rm $TMPBAT

