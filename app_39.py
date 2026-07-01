# ============================================================
# 1日厳選5レース機能 v3
# ------------------------------------------------------------
# v2からの変更点（実データ検証の結果、設計を変更）:
#   - 出走表CSVには「今回のレース」情報（会場・R番号・距離・グレード）が
#     一切含まれていないことが実データで確認された。
#     → CSV内から推定する v2 の guess_race_meta アプローチを廃止。
#   - 代わりに、JRA公式サイトの「開催日程」ページ（番組表）をそのまま
#     コピペしてもらい、そこから会場・R番号・距離・芝ダ・クラス名を取得する。
#   - CSVのレースブロックは「場→R番号の昇順」で並んでいる、という
#     実データで確認された規則性を使い、パースした番組表（対象トラックのみ）
#     と CSV のブロックを順番通りに1:1対応させる。
#   - 対応結果は必ず data_editor で人間が確認・修正できるようにする
#     （同日に同距離のレースが複数ある等、自動対応がズレる可能性があるため）。
#
# 既存の app.py 内の
#   def split_multi_race_csv(...): ...
#   def select_top_gap_races(...): ...
#   （最後の st.header('📅 1日厳選5レース（実験的機能）') 以降ブロック全体）
# を、このファイルの内容で置き換えてください。
# ============================================================

def split_multi_race_csv(file_bytes):
    """
    「枠番」ヘッダー行が複数回出現する、1日分の全レースが縦に連結された
    CSVを、レースごとのDataFrameに分割する。

    Returns: list of (block_no, DataFrame)
        block_no: CSV内での出現順（1始まり）。実データ検証の結果、
                  この順番は「場→R番号の昇順」に一致することを確認済み。
    """
    for enc in ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']:
        try:
            df_raw = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except Exception:
            continue
    else:
        raise ValueError('文字コードを判定できませんでした')

    if '枠番' not in df_raw.columns:
        raise ValueError('「枠番」列が見つかりません。レース区切りを検出できる形式のCSVをアップロードしてください。')

    header_rows = df_raw[df_raw['枠番'].astype(str) == '枠番'].index.tolist()
    boundaries = [0] + header_rows + [len(df_raw)]

    races = []
    block_no = 1
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        block = df_raw.iloc[start:end].copy()
        if len(block) > 0 and str(block.iloc[0]['枠番']) == '枠番':
            block = block.iloc[1:].copy()
        block = block.dropna(subset=['馬名S'])
        block = block[block['馬名S'].astype(str) != '馬名S'].reset_index(drop=True)
        if len(block) < 2:
            continue
        races.append((block_no, block))
        block_no += 1
    return races


# ============================================================
# JRA番組表テキストのパース
# ============================================================
VENUE_NAMES = ['東京', '中山', '京都', '阪神', '新潟', '中京', '福島', '小倉', '札幌', '函館']

# 例: "4レース 3歳未勝利 1,600（芝） 11:35" / "4R 3歳未勝利 1600(芝) 11:35"
#     "9レース 香港ジョッキークラブトロフィー 3歳以上2勝クラス 2,000（芝）混 14:25"
RACE_LINE_RE = re.compile(
    r'(\d{1,2})\s*[RレースＲ]+.*?([\d,，]{3,5})\s*m?\s*[（(]\s*(芝|ダート|ダ)(?:[・][^）)]*)?\s*[)）]',
)

def parse_jra_program(text):
    """
    JRA公式サイトの「開催日程（番組表）」ページ等からコピペしたテキストを解析し、
    会場ごとのレース一覧（R番号・距離・トラック・クラス名）を返す。

    厳密なフォーマットは要求しない（コピペ時の改行崩れなどに耐えるよう、
    「N R ... 距離（芝/ダート）」というパターンをテキスト全体から拾う方式）。
    会場名の行（東京/中山/...などが単独、または「◯回東京◯日目」のように
    含まれる行）が出てきたら、以降のレースをその会場に割り当てる。

    Returns: list of dict [{'venue','race_no','dist','track','line_text'}], 出現順
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    results = []
    current_venue = None

    for line in lines:
        # 会場名を含む行か判定（レース行と誤認しないよう、距離パターンを含まない行のみ）
        if not RACE_LINE_RE.search(line):
            for v in VENUE_NAMES:
                if v in line:
                    current_venue = v
                    break
            continue

        m = RACE_LINE_RE.search(line)
        if not m:
            continue
        race_no = int(m.group(1))
        dist = float(m.group(2).replace(',', '').replace('，', ''))
        track = 'D' if m.group(3) in ('ダート', 'ダ') else 'T'

        results.append({
            'venue': current_venue or '(不明)',
            'race_no': race_no,
            'dist': dist,
            'track': track,
            'line_text': line[:40],
        })

    return results


def select_top_gap_races(race_lpi_results, n_select=5):
    """
    各レースのLPI計算結果から、LPI1位と2位のスコア差(gap)が大きい順にn_select件を選ぶ。
    """
    scored = []
    for r in race_lpi_results:
        ranked = r['ranked']
        if len(ranked) < 2:
            continue
        gap = ranked[0]['avg_venue_lpi'] - ranked[1]['avg_venue_lpi']
        scored.append({**r, 'gap': gap})
    scored.sort(key=lambda x: -x['gap'])
    return scored[:n_select]


st.markdown('---')
st.header('📅 1日厳選5レース（実験的機能 v3）')
st.caption(
    '1日分の全レースが連結された出走表CSVを読み込み、JRA公式サイトの番組表とレース単位で対応づけたうえで、'
    'LPI1位と2位のスコア差(gap)が最も大きい上位レースを自動選定します。'
)
st.info(
    '💡 検証結果（2024-2025年・下級条件込み）: 馬単的中率11.9〜14.3%・回収率134.8〜154.3%（2年連続）。'
    'ただし大穴1〜2件への依存度は年によって変動するため、過信は禁物です。'
)

with st.expander('📅 1日厳選5レースを使う', expanded=False):

    st.markdown('**① 出走表CSVをアップロード**')
    col_a, col_b = st.columns(2)
    with col_a:
        daily_base_file = st.file_uploader(
            '基準テーブル用CSV（重賞 or 平場のbasedate）', type='csv', key='daily_base')
    with col_b:
        daily_multi_file = st.file_uploader(
            'この日の全レース出走表CSV（枠番区切り形式）', type='csv', key='daily_multi')

    daily_n_select = st.slider('厳選するレース数', 1, 10, 5, key='daily_n')

    st.markdown('---')
    st.markdown(
        '**② 番組表をコピペ**　'
        '[JRA開催日程ページ](https://www.jra.go.jp/keiba/calendar/) '
        'でその日を開き、会場ごとの表（会場名〜R番号〜距離〜芝ダ）をそのままコピー＆ペーストしてください。'
        '複数会場ある場合は両方まとめて貼ってOKです。'
    )
    program_text = st.text_area(
        '番組表テキスト', height=200, key='daily_program_text',
        placeholder='例:\n東京\n1レース 3歳未勝利 1,400（ダート）（外） 10:05\n'
                    '...\n4レース 3歳未勝利 1,600（芝） 11:35\n...\n阪神\n2レース 3歳未勝利 1,800（芝・外） 10:20\n...'
    )
    target_track_filter = st.radio('抽出するトラック', ['芝', 'ダート'], horizontal=True, key='daily_track_filter')

    split_btn = st.button('③ CSV分割 + 番組表パース + 自動対応づけ', key='daily_split')

    if split_btn:
        if not daily_multi_file:
            st.error('この日の全レース出走表CSVをアップロードしてください。')
        elif not program_text.strip():
            st.error('番組表テキストを貼り付けてください。')
        else:
            try:
                races = split_multi_race_csv(daily_multi_file.read())
                daily_multi_file.seek(0)
            except Exception as e:
                st.error(f'CSVの分割に失敗しました: {e}')
                races = []

            program = parse_jra_program(program_text)
            track_code = 'T' if target_track_filter == '芝' else 'D'
            program_filtered = [p for p in program if p['track'] == track_code]
            # 場→R番号の昇順に整列（CSVブロックの並び順と一致する前提）
            program_filtered.sort(key=lambda p: (VENUE_NAMES.index(p['venue'])
                                                   if p['venue'] in VENUE_NAMES else 99,
                                                   p['race_no']))

            if not races:
                st.warning('CSVからレースを検出できませんでした。')
            elif not program_filtered:
                st.warning('番組表から対象トラックのレースを検出できませんでした。テキストの形式を確認してください。')
            else:
                n_races, n_prog = len(races), len(program_filtered)
                if n_races == n_prog:
                    st.success(f'✅ CSV{n_races}レース分 と 番組表の{target_track_filter}レース{n_prog}件が一致しました。')
                else:
                    st.warning(
                        f'⚠️ CSVは{n_races}レース分ですが、番組表から拾えた{target_track_filter}レースは{n_prog}件でした。'
                        '対応がズレている可能性があるので、下の表で必ず確認してください。'
                    )

                mapping_rows = []
                for i, (block_no, block) in enumerate(races):
                    p = program_filtered[i] if i < len(program_filtered) else None
                    mapping_rows.append({
                        'block_no': block_no,
                        '頭数': len(block),
                        '会場': p['venue'] if p else None,
                        'R': p['race_no'] if p else None,
                        '距離': p['dist'] if p else None,
                        'トラック': track_code,
                        '検出テキスト': p['line_text'] if p else '',
                    })

                st.session_state['daily_races'] = races
                st.session_state['daily_mapping_df'] = pd.DataFrame(mapping_rows)

    if 'daily_mapping_df' in st.session_state:
        st.markdown('**④ 対応づけの確認・修正**（頭数を見て、明らかにおかしい対応は修正してください）')
        edited_map = st.data_editor(
            st.session_state['daily_mapping_df'],
            column_config={
                '会場': st.column_config.SelectboxColumn('会場', options=VENUE_NAMES),
                'R': st.column_config.NumberColumn('R番号', min_value=1, max_value=12, step=1),
                '距離': st.column_config.NumberColumn('距離(m)', min_value=800, max_value=3600, step=100),
                'トラック': st.column_config.SelectboxColumn('トラック', options=['T', 'D']),
            },
            disabled=['block_no', '頭数', '検出テキスト'],
            hide_index=True,
            use_container_width=True,
            key='daily_map_editor',
        )

        missing = edited_map['距離'].isna().sum() + edited_map['会場'].isna().sum()
        if missing > 0:
            st.warning(f'⚠️ 未確定の項目が{missing}件あります。表を編集して埋めてから計算してください。')

        daily_run = st.button(
            '⑤ 厳選レースを計算する', type='primary', key='daily_run',
            disabled=(missing > 0),
        )

        if daily_run:
            if not daily_base_file:
                st.error('基準テーブルCSVをアップロードしてください。')
            else:
                with st.spinner('基準テーブルを構築中...'):
                    d_base_dict, d_稍重_dict, d_race_base_dict = build_base_table(daily_base_file.read())

                races = st.session_state['daily_races']
                map_by_block = {row['block_no']: row for _, row in edited_map.iterrows()}

                race_lpi_results = []
                progress = st.progress(0)
                for i, (block_no, block) in enumerate(races):
                    m = map_by_block.get(block_no)
                    if m is None:
                        progress.progress((i + 1) / len(races))
                        continue

                    r_dist  = float(m['距離'])
                    r_track = m['トラック'] or 'T'
                    r_venue = m['会場']
                    r_no    = int(m['R']) if pd.notna(m['R']) else None

                    try:
                        # cp932の方がshift_jisよりカバー範囲が広く文字化けしにくい
                        csv_bytes = block.to_csv(index=False).encode('cp932', errors='replace')

                        if abs(r_dist - 1200) <= 100 and r_track == 'T':
                            results = calc_lpi_1200m(
                                csv_bytes, d_base_dict, d_稍重_dict,
                                target_venue=r_venue, target_grade='G3',
                            )
                            ranked = sorted(results, key=lambda x: -x['avg_venue_lpi'])
                            model_used = '1200m専用AI'
                        else:
                            pace = get_pace_prediction(r_dist, r_venue, nige_count=0, senkou_count=0)
                            results = calc_lpi(
                                csv_bytes, d_base_dict, d_稍重_dict,
                                target_track=r_track, target_venue=r_venue,
                                bonus_strength=0.15, pace_pred_rpci=pace['pred_rpci'],
                                race_base_dict=d_race_base_dict,
                            )
                            ranked = sorted(results, key=lambda x: -x['avg_venue_lpi'])
                            model_used = '汎用LPI'

                        if len(ranked) >= 2:
                            race_lpi_results.append({
                                'block_no': block_no, 'race_label': f'{r_venue}{r_no}R' if r_no else r_venue,
                                'n_horses': len(ranked), 'ranked': ranked,
                                'dist': r_dist, 'track': r_track, 'venue': r_venue, 'model': model_used,
                            })
                    except Exception as e:
                        st.caption(f'block{block_no}: 計算スキップ（{e}）')
                    progress.progress((i + 1) / len(races))

                if not race_lpi_results:
                    st.warning('LPIを計算できたレースがありませんでした。')
                else:
                    selected = select_top_gap_races(race_lpi_results, n_select=daily_n_select)

                    st.subheader(f'🏆 本日の厳選{len(selected)}レース（gap = LPI1位と2位のスコア差）')
                    for s in selected:
                        ranked = s['ranked']
                        axis = ranked[0]
                        partners = ranked[1:5]
                        st.markdown(
                            f"**{s['race_label']}**　{int(s['dist'])}m {s['track']}　"
                            f"[{s['model']}]　gap = **{s['gap']:.1f}**　（出走{s['n_horses']}頭）"
                        )
                        rows = [{
                            'LPI順位': 1, '馬名': axis['horse'],
                            'LPI': axis['avg_venue_lpi'], '役割': '🎯 軸（1着固定）',
                        }]
                        for j, p in enumerate(partners, start=2):
                            rows.append({
                                'LPI順位': j, '馬名': p['horse'],
                                'LPI': p['avg_venue_lpi'], '役割': '相手候補（2着）',
                            })
                        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                        st.caption(
                            f"馬単4点: {axis['horse']} → "
                            f"{' / '.join(p['horse'] for p in partners)}"
                        )
                        st.markdown('')

                    st.subheader('📋 全レース一覧（gap順）')
                    all_rows = []
                    for r in sorted(race_lpi_results,
                                     key=lambda x: -(x['ranked'][0]['avg_venue_lpi'] - x['ranked'][1]['avg_venue_lpi'])):
                        gap = r['ranked'][0]['avg_venue_lpi'] - r['ranked'][1]['avg_venue_lpi']
                        is_selected = r['block_no'] in [s['block_no'] for s in selected]
                        all_rows.append({
                            'レース': r['race_label'], '距離': f"{int(r['dist'])}m",
                            'モデル': r['model'], '出走頭数': r['n_horses'],
                            'LPI1位': r['ranked'][0]['horse'], 'LPI2位': r['ranked'][1]['horse'],
                            'gap': round(gap, 1), '厳選対象': '✅' if is_selected else '-',
                        })
                    st.dataframe(pd.DataFrame(all_rows), hide_index=True, use_container_width=True)