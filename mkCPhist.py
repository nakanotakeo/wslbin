#!/bin/python3 
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# コマンドライン引数の処理
parser = argparse.ArgumentParser()
parser.add_argument('csv_file', help='Path to the input CSV file')
args = parser.parse_args()

# csv ファイルを読み込み、2 列目のデータを取得します
df = pd.read_csv(args.csv_file, header=None, encoding='cp932')
data = df[1]

# ヒストグラムの最大値はデータの最大値とします
hist_max = data.max()

# set fontsizes
axis_fontsize = 10
label_fontsize = axis_fontsize * 1.5

plt.xticks(fontsize=axis_fontsize)
plt.yticks(fontsize=axis_fontsize)
plt.xlabel('Score', fontsize=label_fontsize)
plt.ylabel('Frequency', fontsize=label_fontsize)

# define bin boundaries
bins = np.arange(-0.5, hist_max + 1, 1)

# ヒストグラムを描画します
plt.hist(data, bins=bins, range=(0, hist_max), align='mid')

# PNG ファイル名は CSV ファイル名から拡張子を除いたものとします
png_file = os.path.splitext(args.csv_file)[0] + '.png'

# ヒストグラムを PNG ファイルとして保存します
plt.savefig(png_file)

