#!/bin/bash 

date=$(date -d '7 hours ago 30 minutes ago' +%y%m%d)
zipname="RSSs$date.zip"

URLbase="https://surf.st.seikei.ac.jp/~nakano/RSS/"

wget -v -O "$HOME/Dropbox/RSS/$zipname" "$URLbase/$zipname"
# wget -v "$URLbase/$zipname"

