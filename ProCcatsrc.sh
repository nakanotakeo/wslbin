#!/bin/bash
#
# Run from WSL shell. nkf and libreoffice-writer are required.
# run after exe files are properly compiled.
#
LOGBASE=sources
for compc in *.c; do
  echo "=======${compc}=======" >> $LOGBASE.bom
  nkf --oc=UTF-8 $compc         >> $LOGBASE.bom
  echo ""                       >> $LOGBASE.bom
  echo "======================" >> $LOGBASE.bom
  echo ""                       >> $LOGBASE.bom
done

sed 's/\xEF\xBB\xBF//g' $LOGBASE.bom > $LOGBASE.log
rm $LOGBASE.bom
libreoffice --headless --convert-to pdf $LOGBASE.log
