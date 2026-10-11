#!/bin/bash

dir="$HOME/Dropbox/RSS"
URLbase="https://surf.st.seikei.ac.jp/~nakano/RSS"

# 7:30 より前は前日扱い
today=$(date -d '7 hours 30 minutes ago' +%y%m%d)

# ローカルにある最新の ZIP の日付
last=$(find "$dir" -maxdepth 1 -name 'RSSs[0-9][0-9][0-9][0-9][0-9][0-9].zip' \
    -printf '%f\n' | sort | tail -n 1)
last=${last#RSSs}
last=${last%.zip}

# 最後に取得した日の翌日から順に取得
day=$(date -d "20${last:0:2}-${last:2:2}-${last:4:2} +1 day" +%Y-%m-%d)

while [[ $(date -d "$day" +%y%m%d) -le $today ]]; do
    zipname="RSSs$(date -d "$day" +%y%m%d).zip"

    echo "Downloading $zipname"
    wget -v --no-proxy -O "$dir/$zipname" "$URLbase/$zipname"

    day=$(date -d "$day +1 day" +%Y-%m-%d)
done

