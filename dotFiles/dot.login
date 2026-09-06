#!/bin/bash 
setenv LANG ja_JP.UTF-8

KCHOST=`uname -n`
keychain --host $KCHOST ~/.ssh/id_ed25519
source ~/.keychain/$KCHOST-sh

