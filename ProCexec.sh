#!/bin/bash
#
# Run from WSL shell. nkf and libreoffice-writer are required.
# run after exe files are properly compiled.
#
LOGBASE=exec
for compc in *.c; do
  echo "=======${compc}=======" >> $LOGBASE.bom
  nkf --oc=UTF-8 $compc         >> $LOGBASE.bom
  echo ""                       >> $LOGBASE.bom
  echo "======================" >> $LOGBASE.bom
  compexe=`basename $compc .c`.exe
  echo "Run $compexe"
  ./$compexe | nkf --oc=UTF-8 >> $LOGBASE.bom
  echo ""                       >> $LOGBASE.bom
done

sed 's/\xEF\xBB\xBF//g' $LOGBASE.bom > $LOGBASE.log
rm $LOGBASE.bom
libreoffice --headless --convert-to pdf $LOGBASE.log
