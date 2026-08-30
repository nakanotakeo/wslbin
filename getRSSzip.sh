#!/bin/bash 

date=`date +%y%m%d`
zipname="RSSs$date.zip"

URLbase="https://surf.st.seikei.ac.jp/~nakano/RSS/"

wget -v -O "$HOME/Dropbox/RSS/$zipname" "$URLbase/$zipname"
# wget -v "$URLbase/$zipname"

