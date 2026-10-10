# ProCjoinWord2pdf.py マニュアル

## 目的

指定フォルダの Word 文書（`.docx`）を LibreOffice で個別の PDF に変換し、ファイル名の昇順で結合して１つの PDF を作成する。

## 必要な環境

- WSL（Debian）の Python 3。
- WSL 側の LibreOffice Writer。コマンド名 `libreoffice` で起動できること。
- 実行する Python 環境にインストールされた `pypdf`。

Windows の Word を自動操作するスクリプトではない。

Python の仮想環境を使って用意する例：

```bash
sudo apt install python3-venv libreoffice-writer
python3 -m venv ~/venvs/proc
~/venvs/proc/bin/python -m pip install pypdf
```

以降、その環境を有効にして実行する。

```bash
source ~/venvs/proc/bin/activate
```

すでに使用中の Python に `pypdf` が入っている場合は、環境を作り直す必要はない。

## 実行方法

```bash
python3 ~/wslbin/ProCjoinWord2pdf.py 提出物フォルダ 結合PDFの出力先
```

| 引数 | 必須 | 用途 |
| --- | --- | --- |
| 第１引数 | はい | `.docx` が入ったフォルダ |
| 第２引数 | はい | 結合する PDF のファイルパス |

相対パスは、スクリプトの置き場所ではなく、コマンドを実行したカレントディレクトリを基準にする。

例えば、提出フォルダの親で次を実行する。

```bash
python3 ~/wslbin/ProCjoinWord2pdf.py Word提出物 week1reports.pdf
```

空白を含むパスは引用符で囲む。

```bash
python3 ~/wslbin/ProCjoinWord2pdf.py "Word 提出物" "week1 reports.pdf"
```

別の出力フォルダを指定することもできる。出力先の親フォルダがなければ作成する。

```bash
python3 ~/wslbin/ProCjoinWord2pdf.py Word提出物 pdf/week1reports.pdf
```

仮想環境を有効にせず、その Python を直接指定する場合：

```bash
~/venvs/proc/bin/python ~/wslbin/ProCjoinWord2pdf.py Word提出物 week1reports.pdf
```

ヘルプは次のコマンドで表示する。ただし、ヘルプ表示にも `pypdf` のインポートが必要。

```bash
python3 ~/wslbin/ProCjoinWord2pdf.py --help
```

## 入力と結合順序

- 指定フォルダ直下の `.docx` を対象とする。拡張子の大文字・小文字は問わない。
- サブフォルダは検索しない。旧形式の `.doc` は対象外。
- ファイル名を Python の `sorted()` で昇順に並べ、その順に結合する。
- 数字を数値として並べる「自然順」ではない。例えば `report1.docx`、`report10.docx`、`report2.docx` の順になる。順序をそろえる場合は `report01.docx` のように桁数をそろえる。
- Word の一時ファイル `~$名前.docx` も、拡張子の条件に一致すれば対象になる。実行前に提出フォルダから除いておく。

## 出力

| 出力 | 保存先・内容 |
| --- | --- |
| 個別の PDF | 入力フォルダ内。元の `.docx` と同じベース名 |
| 結合 PDF | 第２引数で指定したパス |

例えば `Word提出物/S227083.docx` は `Word提出物/S227083.pdf` に変換される。個別の PDF は処理後も残り、元の `.docx` は変更しない。

指定フォルダに元からある PDF をすべて結合するわけではなく、対象 `.docx` に対応する PDF だけを結合する。各文書のページをそのまま順に追加し、文書間の表紙・区切りページ・通しページ番号は挿入しない。

結合 PDF の同名ファイルがある場合は上書きする。出力先には、個別 PDF と重ならないパスを指定する。

## 処理状況とエラー

LibreOffice の標準出力と標準エラーは非表示にしている。正常終了時にも完了メッセージは表示しないため、出力ファイルを確認する。

```bash
ls -l week1reports.pdf
```

次のような問題があると、例外を表示して途中停止する。

| 症状 | 確認する内容 |
| --- | --- |
| `ModuleNotFoundError: No module named 'pypdf'` | 実行中の Python に `pypdf` が入っているか。仮想環境を有効にしたか |
| `NotADirectoryError` | 第１引数のフォルダが存在するか |
| `libreoffice` が見つからない | WSL 側に LibreOffice がインストールされているか |
| `CalledProcessError` | LibreOffice の変換コマンドが非ゼロで終了している |
| `PDF was not generated` | 対象文書の PDF が生成されていない |

変換失敗の詳細を見るには、対象文書について LibreOffice を直接実行する。

```bash
libreoffice --headless --convert-to pdf --outdir Word提出物 Word提出物/S227083.docx
```

## 現在の実装上の注意

- 対応する個別 PDF が存在するかだけを確認し、今回新しく変換されたかまでは検証しない。既存 PDF がある場合は、必要に応じて更新日時を確認する。
- `.docx` が０件でも、明示的なエラーにはしない。有効なレポートが結合されたとは限らないため、入力件数を確認する。
- 読み取り専用の入力フォルダでは、個別 PDF を保存できない。
- LibreOffice の描画によるため、Word での表示と改ページ・フォントなどが異なる可能性がある。提出文書の結合後に表示を確認する。
