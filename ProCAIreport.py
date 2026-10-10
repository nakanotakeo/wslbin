#!/usr/bin/env python3
"""提出済み AI 会話 HTML の発言回数と相対リンクを採点表の G 列に追加する。

Python 3.9 以降、外部パッケージ不要。

ZIP を通常どおり展開し、report_REP... フォルダと rptevaluation_REP....xlsx
が並んでいる親フォルダを指定する（ZIP ファイル自体は指定しない）。

    python3 ProCAIreport.py ~/Dropbox/ProgrammingC/ProgC2c1_02

そのフォルダを現在の作業場所として実行する場合:

    python3 ../ProCAIreport.py

出力は元の採点表と同じ場所の rptevaluation_AIreport.xlsx。
Excel と同じ場所に ProChtmlAI/ を作り、HTML を英数字名でコピーする。
例: S235023_us235023_02_日本語タイトル.html → ProChtmlAI/S235023_us235023_02.html
名前の学籍番号・ユーザー ID・提出ファイル番号を維持し、日本語タイトルを除く。
Excel の相対リンクはこのコピーに向ける。リンクを設定した評価メモのセルは、
青字・下線のハイパーリンク書式にする。Excel を移動するときは ProChtmlAI/
も一緒に移動し、両者の位置関係を維持する。元の提出 HTML は変更しない。
出力が既にある場合、--force を付けると出力と今回対象の HTML コピーを更新する。

    python3 ProCAIreport.py . --force

採点表が複数ある場合は --xlsx で指定する。指定パスは現在の作業場所からの相対
パスまたは絶対パス。-o で出力先を変えた場合も、その場所から相対リンクを作る。

    python3 ProCAIreport.py . --xlsx rptevaluation_REP000000123_20261010.xlsx

「質問回数」は学生側の送信回数。コード送信、相づち、AI からの質問への回答、
HTML 化の依頼も含む。AI の回答数や疑問符の数ではない。記録された範囲を数え、
未記録の対話は推定しない。今回確認した ChatGPT/Gemini/Claude の保存ページ、
user クラス付き対話ログ、User prompt ラベル、PROMPT バッジ形式に対応。
未知の保存形式や会話本文のない HTML は「質問回数不明」とする。
HTML 内の JavaScript は実行しない。Web サービスへの通信も行わない。

複数 HTML がある学生は送信回数を合計し、先頭 HTML にリンクする。不明を含む
場合は合計も不明。重複ログは自動除外しないので、表示される注意を確認する。
既存の評価メモは保持して追記し、このスクリプトが付けた AI利用(...) の部分は
更新する。既存の数式・他用途のリンクがある G セルは上書きせずエラーにする。
複数の授業回の report_REP... フォルダはまとめて処理せず、回ごとに実行する。

手動で数えた結果を優先するには、UTF-8 の補正 JSON を --counts で指定する。
キーは提出物フォルダからの相対パス（区切りは /）、値は回数または null。

    {"report_REP000000123_20261010/S123456_us123456_01_log.html": 3}
    python3 ProCAIreport.py . --counts counts.json

HTML の構造がサービス側で変わると修正が必要になる場合がある。
実行時に各 HTML の回数・判定方法と、不明件数を表示する。
詳細オプション: python3 ProCAIreport.py --help
"""
import argparse
import copy
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile
from io import BytesIO

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('', NS)
ET.register_namespace('r', REL)
Q = lambda name: '{' + NS + '}' + name
GENERATED = re.compile(r'AI利用\(質問(?:\d+回|回数不明)\) \[リンク\](?:（HTML \d+件）)?')
USER_LABEL = re.compile(r'^(?:あなた(?:の発言|のメッセージ)?|ユーザー|User|Human|You)\s*[:：]?$', re.I)
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
IGNORED = {'script', 'style', 'svg', 'template', 'noscript'}


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def text(self):
        if self.tag in IGNORED:
            return ''
        return ''.join(c if isinstance(c, str) else c.text() for c in self.children)

    def classes(self):
        return set(self.attrs.get('class', '').lower().split())


class LogParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(n)
        self.nodes.append(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def outermost(nodes):
    """入れ子の同一発言を二重に数えない。"""
    selected = set(nodes)
    result = []
    for n in nodes:
        p = n.parent
        while p is not None and p not in selected:
            p = p.parent
        if p is None:
            result.append(n)
    return result


def decode_html(data):
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16')
    match = re.search(br'charset\s*=\s*["\x27]?\s*([\w-]+)', data[:8192], re.I)
    encodings = ['utf-8-sig']
    if match:
        encodings.append(match.group(1).decode('ascii'))
    encodings += ['cp932', 'euc_jp']
    for enc in dict.fromkeys(encodings):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            pass
    return data.decode('utf-8', errors='replace')


def count_questions(path):
    """(回数または None, 判定方法)。構造マーカーを優先し、本文中の疑問符は数えない。"""
    parser = LogParser()
    parser.feed(decode_html(path.read_bytes()))
    visible = []
    for n in parser.nodes:
        p = n
        while p is not None and p.tag not in IGNORED:
            p = p.parent
        if p is None:
            visible.append(n)
    # 同じログ内のマーカー方式は合算しない。優先度の高い一方式だけ使う。
    def role(n):
        return any((n.attrs.get(k) or '').lower() in {'user', 'human'}
                   for k in ('data-message-author-role', 'data-message-role', 'data-role', 'data-author'))
    methods = [
        ('発言者属性', role),
        ('Claude user-message', lambda n: n.attrs.get('data-testid') == 'user-message'),
        ('Gemini user-query', lambda n: n.tag == 'user-query'),
        ('user クラス', lambda n: n.tag in {'div','article','section','li'} and
         bool(n.classes() & {'user','human','user-message','user_message','user-msg','message-user'})),
        ('発言者見出し', lambda n: n.tag in {'h2','h3','h4','h5','h6'} and
         (bool(USER_LABEL.fullmatch(n.text().strip())) or
          bool(re.match(r'^あなたのメッセージ\s*[:：]', n.text().strip())))),
        ('User prompt ラベル', lambda n: n.tag in {'span','p','strong','b'} and
         bool(re.match(r'^User prompt\s*:', n.text().strip(), re.I))),
        ('PROMPT バッジ', lambda n: n.tag in {'span','div'} and
         'badge' in n.classes() and n.text().strip().upper() == 'PROMPT'),
        ('発言者ラベル', lambda n: n.tag in {'div','span','p','strong','b'} and
         bool(n.classes() & {'role','label','speaker'}) and
         bool(USER_LABEL.fullmatch(n.text().strip()))),
    ]
    for method, predicate in methods:
        found = outermost([n for n in visible if predicate(n)])
        if found:
            return len(found), method
    return None, '学生側の発言を識別できません（本文未保存・回答のみ・未対応形式など）'


def cell_text(cell, strings):
    if cell is None:
        return ''
    kind = cell.get('t')
    if kind == 's':
        return strings[int(cell.findtext(Q('v')))]
    if kind == 'inlineStr':
        return ''.join(t.text or '' for t in cell.iter(Q('t')))
    return cell.findtext(Q('v'), '')


def column_number(address):
    number = 0
    for c in re.match(r'[A-Z]+', address).group():
        number = number * 26 + ord(c) - ord('A') + 1
    return number


def widen_memo(sheet):
    """G 列だけ拡幅。既存の連続列定義は分割して他列を保つ。"""
    cols = sheet.find(Q('cols'))
    if cols is None:
        cols = ET.Element(Q('cols'))
        sheet.insert(list(sheet).index(sheet.find(Q('sheetData'))), cols)
    attributes = {'min': '7', 'max': '7', 'width': '36', 'customWidth': '1'}
    for c in list(cols):
        lo, hi = int(c.get('min')), int(c.get('max'))
        if lo <= 7 <= hi:
            attributes.update(c.attrib)
            attributes.update(min='7', max='7', width=str(max(36, float(c.get('width', '0')))), customWidth='1')
            cols.remove(c)
            if lo < 7:
                left = copy.deepcopy(c); left.set('max', '6'); cols.append(left)
            if hi > 7:
                right = copy.deepcopy(c); right.set('min', '8'); cols.append(right)
    cols.append(ET.Element(Q('col'), attributes))
    cols[:] = sorted(cols, key=lambda c: int(c.get('min')))


def hyperlink_cell_style(styles, original_style):
    """元の配置・罫線等を保ち、Hyperlink スタイルの青字・下線を適用する。"""
    fonts = styles.find(Q('fonts'))
    cell_xfs = styles.find(Q('cellXfs'))
    style_xfs = styles.find(Q('cellStyleXfs'))
    if fonts is None or cell_xfs is None or style_xfs is None:
        raise ValueError('Excel の書式定義が不足しています。')

    def reuse_or_add(container, element):
        serialized = ET.tostring(element)
        for index, existing in enumerate(container):
            if ET.tostring(existing) == serialized:
                return index
        container.append(element)
        container.set('count', str(len(container)))
        return len(container) - 1

    def link_font(font_id):
        font = copy.deepcopy(fonts[int(font_id)])
        for child in list(font):
            if child.tag in {Q('color'), Q('u')}:
                font.remove(child)
        ET.SubElement(font, Q('color'), {'theme': '10'})
        ET.SubElement(font, Q('u'), {'val': 'single'})
        return reuse_or_add(fonts, font)

    named = styles.find(Q('cellStyles'))
    if named is None:
        named = ET.Element(Q('cellStyles'), {'count': '0'})
        styles.insert(list(styles).index(cell_xfs) + 1, named)
    hyperlink = next((s for s in named if s.get('builtinId') == '8' or
                      s.get('name') == 'Hyperlink'), None)
    if hyperlink is None:
        base = copy.deepcopy(style_xfs[0])
        base.set('fontId', str(link_font(base.get('fontId', '0'))))
        base.set('applyFont', '1')
        index = reuse_or_add(style_xfs, base)
        hyperlink = ET.SubElement(named, Q('cellStyle'),
                                  {'name': 'Hyperlink', 'xfId': str(index), 'builtinId': '8'})
        named.set('count', str(len(named)))
    xf = copy.deepcopy(cell_xfs[int(original_style)])
    xf.set('fontId', str(link_font(xf.get('fontId', '0'))))
    xf.set('xfId', hyperlink.get('xfId'))
    xf.set('applyFont', '1')
    return reuse_or_add(cell_xfs, xf)


def xml_bytes(element, original=None):
    # Excel 拡張の mc:Ignorable 等が参照する宣言も保存する。
    namespaces = {}
    if original:
        for _, pair in ET.iterparse(BytesIO(original), events=['start-ns']):
            prefix, uri = pair
            namespaces.setdefault(prefix, uri)
            if prefix != 'xml' and not re.fullmatch(r'ns\d+', prefix):
                ET.register_namespace(prefix, uri)
    result = ET.tostring(element, encoding='utf-8', xml_declaration=True)
    if original:
        root_start = result.index(b'<', result.index(b'?>') + 2)
        root_end = result.index(b'>', root_start)
        root_text = result[root_start:root_end]
        additions = b''
        for prefix, uri in namespaces.items():
            name = ('xmlns:'+prefix) if prefix else 'xmlns'
            if not re.search(rb'\s'+re.escape(name.encode())+rb'=', root_text):
                escaped = uri.replace('&','&amp;').replace('"','&quot;').replace('<','&lt;')
                additions += (' '+name+'="'+escaped+'"').encode()
        result = result[:root_end]+additions+result[root_end:]
    return result


def html_copy_name(path):
    """提出ファイルの識別用接頭辞だけを残す。番号を振り直さない。"""
    match = re.match(r'^S([0-9]{6})_+us([0-9]{6})_+([0-9]{2})(?:_|\.|$)', path.name, re.I)
    if not match:
        raise ValueError(f'HTML のコピー名を作れません（Sxxxxxx_usxxxxxx_XX_... の形式が必要）: {path.name}')
    return f'S{match.group(1)}_us{match.group(2)}_{match.group(3)}.html'


def plan_html_copies(logs, output, force):
    """保存前に名前衝突を検出する。実際のコピーは Excel の検証後に行う。"""
    directory = output.parent/'ProChtmlAI'
    plans, seen = [], {}
    for sid, items in sorted(logs.items()):
        for item in items:
            source = item['file']
            target = directory/html_copy_name(source)
            if target in seen and seen[target] != source:
                raise ValueError(f'HTML のコピー名が重複します: {seen[target]} / {source} → {target.name}')
            seen[target] = source
            if target.exists():
                if not target.is_file():
                    raise ValueError(f'HTML のコピー先がファイルではありません: {target}')
                if target.read_bytes() != source.read_bytes() and not force:
                    raise ValueError(f'異なる内容の HTML コピーが存在します: {target}（更新する場合は --force）')
            plans.append((source,target))
    return plans


def save_html_copies(plans):
    for source, target in plans:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() == source.read_bytes():
            continue
        handle, temp_name = tempfile.mkstemp(prefix='ProCAIreport_', suffix='.html', dir=target.parent)
        os.close(handle)
        try:
            shutil.copy2(source, temp_name)
            os.replace(temp_name,target)
        finally:
            Path(temp_name).unlink(missing_ok=True)


def update_workbook(source, output, logs, force=False):
    if source.resolve() == output.resolve():
        raise ValueError('入力 Excel 自体は上書きできません。別の出力名を指定してください。')
    if output.exists() and not force:
        raise ValueError(f'出力が存在します: {output}（上書きする場合は --force）')
    copy_plans = plan_html_copies(logs,output,force)
    copied_paths = {source:target for source,target in copy_plans}
    with ZipFile(source) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    styles = ET.fromstring(parts['xl/styles.xml'])
    strings = []
    if 'xl/sharedStrings.xml' in parts:
        strings = [''.join(t.text or '' for t in si.iter(Q('t')))
                   for si in ET.fromstring(parts['xl/sharedStrings.xml'])]
    workbook = ET.fromstring(parts['xl/workbook.xml'])
    wb_rels = ET.fromstring(parts['xl/_rels/workbook.xml.rels'])
    targets = {r.get('Id'): r.get('Target') for r in wb_rels}
    candidates = []
    for entry in workbook.find(Q('sheets')):
        target = targets[entry.get('{' + REL + '}id')]
        name = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        if name not in parts:
            continue
        sheet = ET.fromstring(parts[name])
        if any(cell_text(c, strings) == '評価メモ' for c in sheet.iter(Q('c'))
               if re.fullmatch(r'G\d+', c.get('r', ''))):
            candidates.append((name, sheet))
    if len(candidates) != 1:
        raise ValueError('G 列に「評価メモ」があるワークシートを一意に選べません。')
    sheet_path, sheet = candidates[0]
    data = sheet.find(Q('sheetData'))
    cells = {c.get('r'): c for c in data.iter(Q('c'))}
    ids = {}
    for row in data:
        nr = row.get('r')
        a, h = cell_text(cells.get('A'+nr), strings), cell_text(cells.get('H'+nr), strings)
        for value in {a, h}:
            match = re.fullmatch(r'(?:us|S)(\d+)', value.strip(), re.I)
            if match:
                key = match.group(1)
                if key in ids and ids[key] != nr:
                    raise ValueError(f'採点表の学生 ID が重複しています: {key}')
                ids[key] = nr
    unmatched = sorted(set(logs) - set(ids))
    if unmatched:
        raise ValueError('採点表に対応行のない HTML があります: ' + ', '.join(unmatched))
    link_path = posixpath.join(posixpath.dirname(sheet_path), '_rels', posixpath.basename(sheet_path)+'.rels')
    rels = ET.fromstring(parts[link_path]) if link_path in parts else ET.Element('{' + PKG + '}Relationships')
    links = sheet.find(Q('hyperlinks'))
    if links is None:
        links = ET.Element(Q('hyperlinks'))
        # OOXML の要素順: hyperlinks は dataValidations の後、printOptions の前。
        before = {Q(n) for n in ('printOptions','pageMargins','pageSetup','headerFooter','rowBreaks',
                  'colBreaks','customProperties','cellWatches','ignoredErrors','smartTags',
                  'drawing','legacyDrawing','legacyDrawingHF','picture','oleObjects','controls',
                  'webPublishItems','tableParts','extLst')}
        index = next((i for i,c in enumerate(sheet) if c.tag in before), len(sheet))
        sheet.insert(index, links)
    used = {r.get('Id') for r in rels}
    changed = []
    for sid, items in sorted(logs.items()):
        nr, address = ids[sid], 'G'+ids[sid]
        cell = cells.get(address)
        old = cell_text(cell, strings)
        if cell is not None and cell.find(Q('f')) is not None:
            raise ValueError(f'{address} に既存の数式があります。元の採点表を指定してください。')
        previous = [link for link in links if link.get('ref') == address]
        if previous and not GENERATED.search(old):
            raise ValueError(f'{address} に既存のリンクがあります。手動確認が必要です。')
        total = None if any(r['count'] is None for r in items) else sum(r['count'] for r in items)
        memo = 'AI利用(質問' + (f'{total}回' if total is not None else '回数不明') + ') [リンク]'
        if len(items) > 1:
            memo += f'（HTML {len(items)}件）'
        kept = GENERATED.sub('', old).strip()
        value = kept + '\n' + memo if kept else memo
        if cell is None:
            row = next(r for r in data if r.get('r') == nr)
            cell = ET.Element(Q('c'), {'r': address})
            index = next((i for i,c in enumerate(row) if c.tag == Q('c') and
                          column_number(c.get('r')) > 7), len(row))
            row.insert(index, cell)
        for child in list(cell):
            cell.remove(child)
        cell.set('t', 'inlineStr')
        cell.set('s', str(hyperlink_cell_style(styles, cell.get('s', '0'))))
        text = ET.SubElement(ET.SubElement(cell, Q('is')), Q('t'))
        text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        text.text = value
        for link in previous:
            rid = link.get('{' + REL + '}id')
            links.remove(link)
            if not any(l.get('{' + REL + '}id') == rid for l in links):
                for relation in list(rels):
                    if relation.get('Id') == rid:
                        rels.remove(relation)
        i = 1
        while f'rIdAI{i}' in used:
            i += 1
        rid = f'rIdAI{i}'; used.add(rid)
        relative = Path(os.path.relpath(copied_paths[items[0]['file']], output.parent)).as_posix()
        ET.SubElement(links, Q('hyperlink'), {'ref': address, '{'+REL+'}id': rid})
        ET.SubElement(rels, '{'+PKG+'}Relationship', {'Id':rid, 'Type':REL+'/hyperlink',
                      'Target':quote(relative, safe='/'), 'TargetMode':'External'})
        changed.append((address, value, relative))
    if not changed:
        raise ValueError('記入対象がありません。')
    widen_memo(sheet)
    parts['xl/styles.xml'] = xml_bytes(styles, parts['xl/styles.xml'])
    parts[sheet_path], parts[link_path] = xml_bytes(sheet, parts[sheet_path]), xml_bytes(rels, parts.get(link_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix='ProCAIreport_', suffix='.xlsx', dir=output.parent)
    os.close(handle)
    try:
        with ZipFile(source) as original, ZipFile(temp_name, 'w') as result:
            for info in original.infolist():
                result.writestr(info, parts[info.filename])
            if link_path not in original.namelist():
                result.writestr(link_path, parts[link_path])
        # 出力を読み直して、メモとリンクが対応していることを確認。
        with ZipFile(temp_name) as result:
            check = ET.fromstring(result.read(sheet_path))
            checked_cells = {c.get('r'):c for c in check.iter(Q('c'))}
            checked_links = {l.get('ref'):l.get('{'+REL+'}id') for l in check.find(Q('hyperlinks'))}
            checked_rels = {r.get('Id'):r.get('Target') for r in ET.fromstring(result.read(link_path))}
            for address, value, relative in changed:
                if cell_text(checked_cells[address], strings) != value or unquote(checked_rels[checked_links[address]]) != relative:
                    raise ValueError(f'出力検証に失敗しました: {address}')
        save_html_copies(copy_plans)
        for address,value,relative in changed:
            if not (output.parent/relative).is_file():
                raise ValueError(f'リンク先 HTML を保存できませんでした: {relative}')
        os.replace(temp_name, output)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return len(changed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('directory', nargs='?', default='.', type=Path, help='ZIP を展開したフォルダ（既定: 現在のフォルダ）')
    parser.add_argument('--xlsx', type=Path, help='採点表を明示指定（省略時は directory 内の rptevaluation_REP*.xlsx を選択）')
    parser.add_argument('-o','--output', type=Path, help='出力パス（既定: 採点表と同じフォルダの rptevaluation_AIreport.xlsx）')
    parser.add_argument('--force', action='store_true', help='既存の出力 Excel と対象 HTML コピーを更新')
    parser.add_argument('--counts', type=Path, help='手動補正 JSON: {"HTML の directory からの相対パス": 回数または null}')
    args = parser.parse_args(argv)
    try:
        directory = args.directory.resolve()
        if not directory.is_dir():
            raise ValueError(f'フォルダがありません: {directory}')
        candidates = sorted(p for p in directory.iterdir() if re.fullmatch(r'rptevaluation_REP[_0-9]+\.xlsx',p.name))
        if args.xlsx:
            source = args.xlsx.resolve()
        elif len(candidates) == 1:
            source = candidates[0]
        else:
            raise ValueError(f'採点表が {len(candidates)} 件あります。--xlsx で 1 件を指定してください。')
        output = args.output.resolve() if args.output else source.parent/'rptevaluation_AIreport.xlsx'
        folders = sorted(p for p in directory.iterdir() if p.is_dir() and re.fullmatch(r'report_REP[_0-9]+',p.name))
        if not folders:
            raise ValueError('report_REP... フォルダがありません。ZIP を展開した親フォルダを指定してください。')
        if len(folders) > 1:
            raise ValueError('report_REP... フォルダが複数あります。授業回ごとにフォルダを分けてください。')
        assignment = re.match(r'rptevaluation_(REP\d+)', source.name)
        if assignment and not folders[0].name.startswith('report_'+assignment.group(1)+'_') and folders[0].name != 'report_'+assignment.group(1):
            raise ValueError('採点表と report_REP... フォルダの REP 番号が異なります。')
        overrides = json.loads(args.counts.read_text(encoding='utf-8-sig')) if args.counts else {}
        if not isinstance(overrides, dict) or any(v is not None and (type(v) is not int or v < 0) for v in overrides.values()):
            raise ValueError('--counts は、相対パスをキー、0 以上の整数または null を値とする JSON にしてください。')
        logs, paths = {}, set()
        for path in sorted(folders[0].rglob('*')):
            if not path.is_file() or path.suffix.lower() not in {'.html','.htm'}:
                continue
            match = re.search(r'(?:^|_)us(\d+)(?:_|\.)', path.name, re.I) or re.match(r'S(\d+)(?:_|\.)', path.name, re.I)
            if not match:
                raise ValueError(f'ファイル名から学生 ID を識別できません: {path.name}')
            key = path.relative_to(directory).as_posix(); paths.add(key)
            if key in overrides:
                count, method = overrides[key], '手動補正'
            else:
                count, method = count_questions(path)
            sid = match.group(1)
            logs.setdefault(sid, []).append({'file':path,'count':count})
            print(f'{"不明" if count is None else str(count)+"回"}\t{key}\t{method}')
        if set(overrides) - paths:
            raise ValueError('手動補正に該当しないパスがあります: ' + ', '.join(sorted(set(overrides)-paths)))
        if not logs:
            raise ValueError('HTML がありません。出力は作成しません。')
        changed = update_workbook(source, output, logs, args.force)
        unknown = sum(any(i['count'] is None for i in items) for items in logs.values())
        print(f'保存: {output}\nHTML コピー先: {output.parent/"ProChtmlAI"}\n記入: {changed}名、質問回数不明: {unknown}名')
        for sid, items in logs.items():
            if len(items)>1:
                print(f'注意: S{sid} は HTML {len(items)} 件の合計です。リンクは先頭ファイルです。ログの重複は手動で確認してください。',file=sys.stderr)
        return 0
    except (ValueError, OSError, KeyError, IndexError, BadZipFile, ET.ParseError) as exc:
        print(f'エラー: {exc}',file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
