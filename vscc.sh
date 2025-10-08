#!/bin/bash
#
# Run from WSL shell. nkf is required.
# Visual Studio 2022 Community should be installed.
# It doesn't work when the current directory is on the UNC path,
# namely, it doesn't work on a WSL native filepath. It is because
# Home directory on the WSL is actually \\wsl.localhost\Debian\home\user\.
#
# It works well when the symlink of the Windows' Dropbox folder is
# placed on a WSL directory, and when the user has been moved to it.
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

