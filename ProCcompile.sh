#!/bin/bash
#
# Run from WSL shell. nkf is required. Visual Studio 2022 Community should also be installed.
# usXXXXXX_TheirName.c is assumed at the subdirectory to be given as a command line option.
# You can log the output of cl.exe by redirecting the command | nkf -w > foo.log
#
if [ $# -ne 1 ]; then
  echo "Usage: $0 [Cfolder]";
  exit 1
fi
FOLDER=$1

TMPBAT=temp_$$.bat
cat << 'EOS' > ./$TMPBAT
chcp 65001
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
for %%i in (*.c) do (
  cl.exe %%i
)
EOS

for subc in $FOLDER/*.c; do
  compc=`basename $subc | cut -d _ -f 1`.c
  echo $subc $compc
  nkf -Lw --oc=UTF-8-BOM "$subc" > $compc
done

cmd.exe /c $TMPBAT

rm $TMPBAT

PS1FILE=execall.ps1
execlog=ExecAll.log
# echo "chcp 65001" > $PS1FILE
for exe in *.exe; do
    src=`basename $exe .exe`.c
    echo "Write-Output -InputObject \"[List $src]\"" >> $PS1FILE
    echo "Get-Content .\\$src" >> $PS1FILE
    echo "Write-Output -InputObject \"[Exec $exe]\" >> $PS1FILE
    echo "pause" >> $PS1FILE
    echo ".\\$exe >> $PS1FILE
done
