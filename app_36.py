"""
LPI v11 競馬予想 Streamlit アプリ
=====================================
起動方法:
  streamlit run app.py

必要なパッケージ:
  pip install streamlit pandas numpy matplotlib openpyxl
"""

import streamlit as st
import pandas as pd
import numpy as np
import math
import re
import io
from collections import Counter

# ============================================================
# ページ設定
# ============================================================
st.set_page_config(
    page_title="LPI v11 競馬予想",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 定数（変更不要）
# ============================================================
SIGMOID_CENTER = -1.755
SIGMOID_SCALE  = 2.972
GOOD_BABA      = {'良', '稍'}

FULL_VENUE = {
    '東京':'東京','中山':'中山','京都':'京都','阪神':'阪神','新潟':'新潟',
    '中京':'中京','福島':'福島','小倉':'小倉','札幌':'札幌','函館':'函館',
}
GRADE_BONUS  = {'G1':1.5,'G2':1.2,'G3':1.0,'L':0.9,'OP':0.8,'':0.7}
GRADE_WEIGHT = {'G1':4.0,'G2':3.0,'G3':2.0,'L':1.5,'OP':0.6,'':0.5}
RANK_BONUS_MULT       = {1:1.5, 2:1.2, 3:1.0}
G1_PENALTY_THRESHOLD  = 0.7
G1_PENALTY_COEF       = 0.70
WEIGHT_BASE           = 56
WEIGHT_PER_KG         = 0.2
WEIGHT_TABLE = {
    ('G1','senior'):(58,56),('G2','senior'):(57,55),('G3','senior'):(56,54),
    ('G1','3yo'):(57,55),  ('G2','3yo'):(56,54),   ('G3','3yo'):(55,53),
    ('L','senior'):(56,54),('OP','senior'):(56,54), ('','senior'):(56,54),
    ('L','3yo'):(55,53),  ('OP','3yo'):(55,53),    ('','3yo'):(55,53),
}

VENUE_ELEMENT_COEF = {
    '東京': {'基礎スピード・パワー':0.77,'ロンスパ・ギアチェンジ':1.20,
             'ギアチェンジ':1.28,'ロンスパ':0.44,'パワー・ロンスパ':1.08},
    '中山': {'基礎スピード・パワー':1.25,'ロンスパ・ギアチェンジ':1.15,
             'ギアチェンジ':0.90,'ロンスパ':1.10,'パワー・ロンスパ':1.00},
    '京都': {'基礎スピード・パワー':1.07,'ロンスパ・ギアチェンジ':1.29,
             'ギアチェンジ':1.05,'ロンスパ':0.76,'パワー・ロンスパ':0.81},
    '阪神': {'基礎スピード・パワー':1.05,'ロンスパ・ギアチェンジ':1.29,
             'ギアチェンジ':1.30,'ロンスパ':0.39,'パワー・ロンスパ':0.89},
    '中京': {'基礎スピード・パワー':1.20,'ロンスパ・ギアチェンジ':1.10,
             'ギアチェンジ':1.25,'ロンスパ':0.70,'パワー・ロンスパ':0.95},
    '新潟': {'基礎スピード・パワー':0.77,'ロンスパ・ギアチェンジ':1.02,
             'ギアチェンジ':1.41,'ロンスパ':0.26,'パワー・ロンスパ':0.87},
    '福島': {'基礎スピード・パワー':1.20,'ロンスパ・ギアチェンジ':1.15,
             'ギアチェンジ':0.90,'ロンスパ':1.05,'パワー・ロンスパ':1.00},
    '小倉': {'基礎スピード・パワー':1.10,'ロンスパ・ギアチェンジ':1.15,
             'ギアチェンジ':1.20,'ロンスパ':0.60,'パワー・ロンスパ':0.95},
    '札幌': {'基礎スピード・パワー':1.05,'ロンスパ・ギアチェンジ':1.20,
             'ギアチェンジ':1.00,'ロンスパ':1.10,'パワー・ロンスパ':1.05},
    '函館': {'基礎スピード・パワー':1.10,'ロンスパ・ギアチェンジ':1.20,
             'ギアチェンジ':0.90,'ロンスパ':1.10,'パワー・ロンスパ':1.05},
}




# ============================================================
# ペース予測テーブル（コース×距離の統計的RPCI傾向）
# 出典: 2023〜2026年全距離重賞 376レース分析
# ============================================================
PACE_TABLE = {
    (1200,'函館'): (45.9,2.5, 0,83), (1200,'中山'): (46.6,4.0, 0,57),
    (1200,'京都'): (48.3,3.1,22,56), (1200,'中京'): (49.8,1.8,10,10),
    (1200,'小倉'): (48.5,3.0,10,40), (1200,'阪神'): (47.8,3.2,10,50),
    (1400,'阪神'): (46.5,2.8,10,70), (1400,'中京'): (47.4,2.8, 0,43),
    (1400,'京都'): (49.9,2.6,22,22), (1400,'東京'): (51.7,2.3,43, 0),
    (1600,'中京'): (48.9,2.3,17,33), (1600,'中山'): (49.9,2.3,22,28),
    (1600,'京都'): (51.2,3.8,44,19), (1600,'東京'): (51.4,3.1,57,14),
    (1600,'阪神'): (52.8,3.8,52,14), (1600,'新潟'): (54.4,2.6,83, 0),
    (1800,'小倉'): (46.5,2.7, 0,60), (1800,'札幌'): (50.8,2.3,50,17),
    (1800,'中山'): (50.9,4.2,31,19), (1800,'福島'): (51.4,1.6,29, 0),
    (1800,'阪神'): (52.7,4.2,43,14), (1800,'東京'): (54.7,4.1,72, 6),
    (2000,'小倉'): (48.8,3.5,20,40), (2000,'阪神'): (49.7,1.9,12,12),
    (2000,'福島'): (50.1,4.8,33,50), (2000,'京都'): (51.5,4.9,44,22),
    (2000,'中山'): (51.8,3.4,55,23), (2000,'中京'): (52.4,5.0,55,18),
    (2000,'新潟'): (55.7,2.7,86, 0), (2000,'東京'): (56.0,4.0,86, 0),
    (2200,'中山'): (52.0,3.7,60,30), (2200,'京都'): (56.2,4.2,82, 0),
    (2400,'京都'): (52.9,3.5,60, 0), (2400,'東京'): (54.5,3.9,79, 7),
    (2500,'中山'): (53.5,3.5,65,10),
}


def get_pace_prediction(dist, venue, nige_count=0, senkou_count=0):
    """
    コース×距離の統計からペースを予測。
    Returns dict: pred_rpci, slow_pct, fast_pct, label, lamp, elem_adv, comment
    """
    key = (float(dist), venue)
    if key not in PACE_TABLE:
        base_avg = 48.0 + (float(dist) - 1200) / 400
        return dict(pred_rpci=round(base_avg,1), base_rpci=round(base_avg,1),
                    std=3.5, slow_pct=30, fast_pct=30,
                    label='データ不足', lamp='⚪', elem_adv=[], comment='コースデータ不足')
    base_avg, std, slow_pct, fast_pct = PACE_TABLE[key]
    pred_rpci = round(base_avg - (nige_count * 0.8 + senkou_count * 0.3), 1)
    if   slow_pct >= 70: label, lamp = '★スロー確定', '🟠'
    elif fast_pct >= 60: label, lamp = '★ハイ確定',   '🔵'
    elif slow_pct >= 50: label, lamp = 'スロー傾向',   '🟠'
    elif fast_pct >= 40: label, lamp = 'ハイ傾向',     '🔵'
    else:                label, lamp = 'どちらも',     '⚪'
    if slow_pct >= 50:
        elem_adv = ['ギアチェンジ', 'ロンスパ・ギアチェンジ']
        comment = f'スロー率{slow_pct}% — GC型有利、先行馬の前残りも警戒'
    elif fast_pct >= 40:
        elem_adv = ['基礎スピード・パワー', 'パワー・ロンスパ']
        comment = f'ハイ率{fast_pct}% — 基礎スピード型有利、差し馬が届きやすい'
    else:
        elem_adv = []
        comment = 'どちらも起こりうる — 逃げ・先行馬の顔触れに注意'
    if nige_count >= 2:
        comment += f'（逃げ{nige_count}頭→ハイ寄り）'
    elif nige_count == 0 and slow_pct >= 50:
        comment += '（逃げ不在→更にスロー化の可能性）'
    return dict(pred_rpci=pred_rpci, base_rpci=base_avg, std=std,
                slow_pct=slow_pct, fast_pct=fast_pct,
                label=label, lamp=lamp, elem_adv=elem_adv, comment=comment)

# ============================================================
# 上がり予測スコア
# 過去走のZスコア（コース補正済み上がり）から予測
# 検証結果: 相関r=0.27, A評価のZ平均=+0.38（C評価=-0.24）
# 競馬場ごとの基準上がりは base_dict / 稍重_dict を使用
# ============================================================

# ============================================================
# クッション値補正
# 基準クッション値=9.0。これより低い（軟）ほど上がりが遅くなる
# 補正式: (9.0 - cushion) × 0.15秒
# ============================================================
def calc_cushion_adj(cushion_val, base_cushion=9.0, coef=0.15):
    """クッション値から基準上がりへの補正値を計算"""
    if cushion_val is None:
        return 0.0
    return round((base_cushion - float(cushion_val)) * coef, 3)


# ============================================================
# ペース調整済みZスコア用 回帰係数テーブル
# 基準上がり = intercept + slope × 前半1F平均
# データ: 2020〜2026年全重賞 良馬場 (scipy.stats.linregress)
# 使用条件: PCI追走スコア機能がONかつtarget_front_1fが設定されている場合
# ============================================================
PACE_REGRESSION = {
    # (距離, 競馬場): (slope, intercept, r)
    (1000,'新潟'): (-0.9014, 43.1328, -0.245),
    (1200,'中京'): (-0.8246, 43.5797, -0.235),
    (1200,'中山'): (-2.3241, 60.6847, -0.384),
    (1200,'京都'): (-1.0894, 46.6041, -0.288),
    (1200,'函館'): (-0.6987, 42.7827, -0.185),
    (1200,'阪神'): (-2.5037, 62.9901, -0.522),
    (1400,'中京'): (-2.4420, 63.1369, -0.408),
    (1400,'京都'): (-0.7545, 43.1096, -0.216),
    (1400,'新潟'): (-2.1218, 59.7741, -0.524),
    (1400,'阪神'): (-1.8358, 56.0789, -0.371),
    (1600,'中京'): (-2.0492, 59.2988, -0.424),
    (1600,'京都'): (-1.3379, 50.5699, -0.228),
    (1600,'新潟'): (-1.2365, 48.9491, -0.281),
    (1600,'東京'): (-1.8148, 55.7700, -0.393),
    (1600,'阪神'): (-2.7806, 67.3822, -0.536),
    (1800,'中山'): (-1.3497, 51.7929, -0.264),
    (1800,'京都'): (-1.7638, 55.8201, -0.487),
    (1800,'函館'): (-2.0303, 60.1176, -0.299),
    (1800,'小倉'): (-3.8866, 81.7728, -0.463),
    (1800,'新潟'): (-2.4851, 63.9123, -0.560),
    (1800,'東京'): (-1.5440, 52.8859, -0.399),
    (1800,'阪神'): (-1.7165, 55.0031, -0.426),
    (2000,'中京'): (-1.9410, 58.6839, -0.400),
    (2000,'函館'): (-4.1172, 85.4790, -0.384),
    (2000,'小倉'): (-2.7953, 69.3979, -0.352),
    (2000,'新潟'): (-5.4022,100.2316, -0.746),
    (2000,'東京'): (-2.5017, 64.7120, -0.430),
    (2000,'阪神'): (-1.6045, 54.8995, -0.253),
    (2200,'中京'): (-3.2844, 75.9519, -0.330),
    (2200,'京都'): (-3.5713, 78.6825, -0.585),
    (2200,'阪神'): (-3.4860, 77.8011, -0.535),
    (2400,'京都'): (-3.3681, 76.8036, -0.554),
    (2400,'東京'): (-3.2628, 74.8698, -0.337),
    (2500,'中山'): (-1.7467, 57.7793, -0.188),
    (2500,'東京'): (-4.0804, 85.1470, -0.632),
}

def get_pace_adjusted_base(dist, venue, target_front_1f):
    """
    今回のペース（target_front_1f）に対応したコース基準上がりを返す。
    回帰式: 基準 = intercept + slope × target_front_1f
    登録なし → None（固定基準を使う）
    """
    key = (float(dist), str(venue))
    if key not in PACE_REGRESSION:
        return None
    slope, intercept, r = PACE_REGRESSION[key]
    return round(intercept + slope * target_front_1f, 3)

# 競馬場×距離の基準上がり（上がり予測の補正に使用）
# 対象コースで上がりが速くなる/遅くなる傾向を補正
COURSE_AGARI_BASE = {
    # (距離, 競馬場): 良馬場の基準上がり秒数
    # 数値が小さいコース = 上がりが速いコース = 高い数値のZが出やすい
    (1200,'東京'): 33.98, (1200,'中山'): 34.29, (1200,'阪神'): 34.06,
    (1200,'中京'): 34.11, (1200,'京都'): 33.93, (1200,'新潟'): 33.85,
    (1400,'東京'): 34.10, (1400,'阪神'): 34.27, (1400,'中京'): 34.22,
    (1600,'東京'): 34.38, (1600,'中山'): 34.51, (1600,'阪神'): 34.46,
    (1600,'京都'): 34.28, (1600,'中京'): 34.27, (1600,'新潟'): 34.41,
    (1800,'東京'): 34.63, (1800,'中山'): 35.08, (1800,'阪神'): 34.85,
    (2000,'東京'): 34.35, (2000,'中山'): 35.36, (2000,'阪神'): 35.55,
    (2000,'京都'): 34.86, (2000,'中京'): 34.97,
    (2200,'京都'): 34.83, (2200,'阪神'): 35.25,
    (2400,'東京'): 35.22, (2400,'京都'): 34.91,
    (2500,'中山'): 35.74,
}

def predict_agari(past_runs, target_dist, target_venue, target_baba='良',
                  predicted_pace_cat=None, pred_gap=None, pci_cs_score=None,
                  cushion_correction=0.0, base_dict_for_z=None,
                  pace_target_front_1f=None):
    """
    上がり予測 v3：全走平均Z + 先行×H消耗補正

    設計方針:
    1. ペース帯別分類をやめて全走の加重平均Zを使う
       （H/M/S分類の精度向上効果がr=0.284と同じことが判明）
    2. 先行（地点差≤0.4）×H走（RPCI≤47）は消耗走として重み×0.3
       （能力ではなく展開の犠牲なので過小評価を防ぐ）
    3. 予測ポジション（pred_gap）で位置取り補正（既存維持）
    """
    GRADE_THRESH = {'A': 0.458, 'C': -0.341}

    # 全有効走を収集
    # target_front_1fが設定されている場合はペース調整済みZを使う
    all_runs_data = []
    for r in past_runs:
        if r.get('excluded_baba') or r.get('excluded_track'):
            continue
        z = r.get('z')
        if z is None or math.isnan(float(z)):
            continue
        z = float(z)
        rpci    = r.get('rpci', 50)
        gap_est = r.get('gap_est', 0.7)
        grade   = r.get('grade', '')
        agari   = r.get('agari')
        dist    = r.get('dist')
        venue   = r.get('venue')
        fp_z    = r.get('front_pace_z')
        pci     = r.get('pci')

        # ペース調整済みZ: PCI既知の走は常にペース調整済みZを使う
        # （PCI追走スコアON/OFFに関係なく、PCIデータがあれば適用）
        z_use = z  # デフォルトは固定基準Z
        if (target_dist is not None and target_venue is not None and
                pci is not None and agari is not None):
            try:
                pci_f   = float(pci); agari_f = float(agari)
                run_front_1f = (pci_f + 50) * agari_f / 100 / 3
                # その走のペースに対応した基準上がり
                pace_base = get_pace_adjusted_base(
                    float(str(dist).replace('m','')),
                    str(venue),
                    run_front_1f
                )
                if pace_base is not None:
                    # stdは通常の基準テーブルから
                    _base_dict = base_dict_for_z or {}
                    _, std_val = _base_dict.get(
                        (float(str(dist).replace('m','')), str(venue)), (pace_base, 1.0))
                    std_val = std_val if std_val and std_val > 0 else 1.0
                    z_use = (pace_base - agari_f) / std_val
            except Exception:
                z_use = z  # フォールバック

        chase_bonus = 0.0
        if fp_z is not None and not math.isnan(float(fp_z)):
            fp_z_f = float(fp_z)
            if fp_z_f < -0.3 and z_use > 0.3:
                chase_bonus = round(min(abs(fp_z_f) * z_use * 0.15, 0.4), 3)
        # コース・距離の一致度による重み
        course_w = calc_course_weight(
            dist, venue, target_dist, target_venue
        ) if (dist is not None and venue is not None) else 1.0

        all_runs_data.append({
            'z': z_use + chase_bonus, 'rpci': float(rpci),
            'gap_est': float(gap_est), 'grade': grade,
            'course_w': course_w,
        })

    if not all_runs_data:
        return None

    # ===== G1/G2限定フィルター（自動判定）=====
    # 条件: G1/G2走のZ平均 と 下位クラス走のZ平均 の差が大きい場合
    # → 下位クラスでZ水増しされている → G1/G2走のみ使用
    high_grade_runs = [r for r in all_runs_data if r['grade'] in ('G1','G2')]
    lower_runs      = [r for r in all_runs_data if r['grade'] not in ('G1','G2','G3','L')]

    use_high_grade_only = False
    if len(high_grade_runs) >= 1 and len(lower_runs) >= 1:
        z_high  = np.mean([r['z'] for r in high_grade_runs])
        z_lower = np.mean([r['z'] for r in lower_runs])
        # 下位クラスのZが上位クラスより0.5以上高い → 水増しと判定
        if z_lower - z_high > 0.5:
            use_high_grade_only = True
    # PCI-CS明示的に△以下の場合も適用（従来の条件を維持）
    if (pci_cs_score is not None and
            pci_cs_score < 0.5 and
            len(high_grade_runs) >= 1):
        use_high_grade_only = True

    source_runs = high_grade_runs if use_high_grade_only else all_runs_data

    # weighted_zs を構築（先行×H消耗補正 × コース距離重み）
    weighted_zs = []
    for r in source_runs:
        is_senkou_H = (r['gap_est'] <= 0.4 and r['rpci'] <= 47)
        pace_w   = 0.3 if is_senkou_H else 1.0
        course_w = r.get('course_w', 1.0)
        weight   = round(pace_w * course_w, 3)
        weighted_zs.append((r['z'], weight))

    if not weighted_zs:
        # G1/G2走しか使わないモードで0件の場合は全走を使う
        weighted_zs = [
            (r['z'],
             round((0.3 if (r['gap_est']<=0.4 and r['rpci']<=47) else 1.0)
                   * r.get('course_w', 1.0), 3))
            for r in all_runs_data
        ]

    if not weighted_zs:
        return None

    # 加重平均Z（消耗走は重み0.3）
    total_w = sum(w for _, w in weighted_zs)
    pred_z  = sum(z * w for z, w in weighted_zs) / total_w if total_w > 0 else 0.0
    pred_z  = round(pred_z, 3)
    all_z_list = [z for z, _ in weighted_zs]

    # PCI追走スコアによるZ割引
    # 速い前半ペースへの対応実績がない馬のZを割り引く
    # ◎(≥2.0)→×1.0 / ○(0.5〜2.0)→×0.85 / △(-0.5〜0.5)→×0.70 / ×(<-0.5)→×0.55
    pci_cs_coef = 1.0
    if pci_cs_score is not None:
        if pci_cs_score >= 2.0:    pci_cs_coef = 1.00
        elif pci_cs_score >= 0.5:  pci_cs_coef = 0.85
        elif pci_cs_score >= -0.5: pci_cs_coef = 0.70
        else:                      pci_cs_coef = 0.55
    pred_z = round(pred_z * pci_cs_coef, 3)

    # 安定度
    z_std = float(np.std(all_z_list, ddof=1)) if len(all_z_list) >= 2 else 0.8
    if z_std <= 0.4:   confidence = '◎安定'
    elif z_std <= 0.7: confidence = '○やや安定'
    else:              confidence = '△不安定'

    # グレード判定（全体基準）
    if pred_z >= GRADE_THRESH['A']:
        grade, grade_label = 'A', '🔴 切れ味A'
    elif pred_z < GRADE_THRESH['C']:
        grade, grade_label = 'C', '⚪ 切れ味C'
    else:
        grade, grade_label = 'B', '🟡 切れ味B'

    n_discounted = sum(1 for _, w in weighted_zs if w < 0.9)
    grade_filter_note = ''
    if use_high_grade_only:
        grade_filter_note = f'（PCI-CS△以下のためG1/G2走{len(high_grade_runs)}件のみ使用）'
    comment = (f'全走Z平均={pred_z:+.2f}（PCI-CS係数×{pci_cs_coef:.2f}適用後）{grade_filter_note}。'
               f'{"上位33%の切れ味" if grade=="A" else "下位33%の末脚" if grade=="C" else "標準的な末脚"}。')
    if n_discounted > 0:
        comment += f' 先行×H消耗走{n_discounted}件は重み0.3で補正済み。'
    if pci_cs_coef < 1.0:
        comment += f' PCI追走スコア{pci_cs_score:.2f}→Z×{pci_cs_coef:.2f}で割引。'

    # 予測上がり秒数（コース基準 − Z + 位置取り補正 + クッション値補正）
    # ペース基準の優先順位:
    #   1. pace_target_front_1f（サイドバー入力値）→ 最優先
    #   2. predicted_pace_cat（H/M/S）からFRONT_PACE_BASEで推定
    #   3. COURSE_AGARI_BASE の固定基準（フォールバック）
    if pace_target_front_1f is not None:
        _front_for_base = pace_target_front_1f
    elif predicted_pace_cat is not None:
        # H/M/SペースからFRONT_PACE_BASEで代表前半1Fを推定
        _dist_key = min(FRONT_PACE_BASE.keys(),
                        key=lambda d: abs(d - float(target_dist)))
        _base_front, _std_front = FRONT_PACE_BASE[_dist_key]
        if predicted_pace_cat == 'H':
            _front_for_base = _base_front - 0.24  # H = 基準より0.24秒速い（実測値）
        elif predicted_pace_cat == 'S':
            _front_for_base = _base_front + 0.21  # S = 基準より0.21秒遅い（実測値）
        else:
            _front_for_base = _base_front          # M = 基準値
    else:
        _front_for_base = None

    pace_adj_base = None
    if _front_for_base is not None:
        pace_adj_base = get_pace_adjusted_base(
            float(target_dist), str(target_venue), _front_for_base)

    if pace_adj_base is not None:
        course_base = pace_adj_base
    else:
        course_base = COURSE_AGARI_BASE.get((float(target_dist), target_venue), 34.5)
    if str(target_baba).strip() == '稍':
        course_base += 0.4
    # クッション値補正を加算
    if cushion_correction != 0.0:
        course_base = round(course_base + cushion_correction, 3)
    GAP_CORRECTION = 0.383
    BASE_GAP       = 0.7
    if pred_gap is not None:
        gap_adj    = GAP_CORRECTION * (pred_gap - BASE_GAP)
        pred_agari = round(course_base - pred_z + gap_adj, 1)
        gap_note   = f'（位置取り補正: 地点差{pred_gap:.1f}秒 {gap_adj:+.2f}秒）'
    else:
        pred_agari = round(course_base - pred_z, 1)
        gap_note   = '（位置取り不明: 地点差0.7秒想定）'

    return {
        'pace_cat':     None,
        'pred_z':       pred_z,
        'z_by_pace':    {'H': None, 'M': None, 'S': None},
        'n_by_pace':    {'H': 0, 'M': 0, 'S': 0},
        'grade':        grade,
        'grade_label':  grade_label,
        'pred_agari':   pred_agari,
        'gap_note':     gap_note,
        'course_base':  course_base,
        'confidence':   confidence,
        'z_std':        round(z_std, 3),
        'comment':      comment,
        'n_valid':      len(weighted_zs),
        'n_discounted': n_discounted,
        'past_zs':      [round(z, 2) for z, _ in weighted_zs],
    }


POS_ZONE_LABELS = {
    1: ('逃げ',  '平均0.1以下',  '#1A237E', '🟦'),
    2: ('先行',  '0.2〜0.4秒',   '#1B5E20', '🟩'),
    3: ('中団',  '0.5〜1.0秒',   '#E65100', '🟨'),
    4: ('後方',  '1.1秒〜',      '#B71C1C', '🟥'),
}

def gap_to_zone(gap):
    """地点差(秒) → ポジション帯番号"""
    if gap is None or (isinstance(gap, float) and math.isnan(gap)):
        return None
    if gap <= 0.1: return 1
    if gap <= 0.4: return 2
    if gap <= 1.0: return 3
    return 4

def predict_position(past_gaps, rpci_pred=None):
    """
    過去走の地点差リスト → ポジション予測。

    Args:
        past_gaps: 過去走の地点差リスト（新しい順）。Noneは除外。
        rpci_pred: 予測RPCI。スロー/ハイによる補正に使用。

    Returns:
        dict: {
          'pred_gap':     予測地点差（秒）,
          'pred_zone':    予測ゾーン番号（1〜4）,
          'label':        'ゾーン名（範囲）',
          'confidence':   '◎安定/○やや安定/△不安定',
          'icon':         絵文字,
          'color':        カラーコード,
          'gap_std':      過去走の地点差std,
          'n_valid':      有効走数,
        }
    """
    valid_gaps = [g for g in past_gaps if g is not None and not math.isnan(float(g))]
    if not valid_gaps:
        return None

    # 直近重み付き平均（1走前50%・2走前30%・3走前以前20%）
    weights = [0.50, 0.30, 0.15, 0.05]
    total_w, weighted_sum = 0.0, 0.0
    for i, g in enumerate(valid_gaps[:4]):
        w = weights[i] if i < len(weights) else 0.05
        weighted_sum += g * w
        total_w += w
    pred_gap = round(weighted_sum / total_w, 2) if total_w > 0 else valid_gaps[0]

    # RPCIによる補正（スロー→縦長化抑制, ハイ→縦長化）
    # スローでは馬群がコンパクトになる傾向（地点差std↓）
    if rpci_pred is not None:
        if rpci_pred >= 54:    pred_gap -= 0.05   # 超スロー: やや前詰まり
        elif rpci_pred <= 46:  pred_gap += 0.05   # 超ハイ: やや後ろ広がり

    pred_gap = max(0.0, pred_gap)
    pred_zone = gap_to_zone(pred_gap)

    # 安定度（std）
    if len(valid_gaps) >= 2:
        gap_std = float(np.std(valid_gaps, ddof=1))
    else:
        gap_std = 0.5  # デフォルト

    # 安定度ラベル
    if gap_std <= 0.25:   confidence = '◎安定'
    elif gap_std <= 0.45: confidence = '○やや安定'
    else:                 confidence = '△不安定'

    zone_info = POS_ZONE_LABELS.get(pred_zone, (str(pred_zone),'','#888','⚪'))

    return {
        'pred_gap':   pred_gap,
        'pred_zone':  pred_zone,
        'zone_name':  zone_info[0],
        'zone_range': zone_info[1],
        'label':      f"{zone_info[0]}（{zone_info[1]}）",
        'confidence': confidence,
        'icon':       zone_info[3],
        'color':      zone_info[2],
        'gap_std':    round(gap_std, 3),
        'n_valid':    len(valid_gaps),
        'past_gaps':  valid_gaps,
    }


# ============================================================
# 前半ペース速度（追走能力）の評価
# PCIから前半1F平均を逆算: Ave3F = (PCI+50) × 上がり / 100
# 前半1F = Ave3F / 3
# 距離別基準（良馬場・2020〜2026年重賞実測値）
# ============================================================
FRONT_PACE_BASE = {
    # 距離: (1F平均基準秒, std)
    1000: (11.244, 0.219),
    1200: (11.462, 0.253),
    1400: (11.674, 0.269),
    1500: (12.123, 0.160),
    1600: (11.840, 0.220),
    1800: (12.045, 0.247),
    2000: (12.117, 0.214),
    2200: (12.131, 0.177),
    2400: (12.248, 0.169),
    2500: (12.323, 0.178),
    3000: (12.400, 0.200),  # 推定値
    3200: (12.420, 0.200),  # 推定値
}

def calc_front_pace_z(pci, agari, dist):
    """
    PCIと上がりから「前半ペースZスコア」を計算。
    
    前半1F平均 = (PCI+50) × 上がり / 100 / 3
    前半ペースZ = (基準1F - 実際1F) / std
      → マイナス = 前半が速い（追走がきつい）
      → プラス   = 前半が遅い（スロー）
    
    Returns:
        float or None: 前半ペースZスコア
    """
    try:
        pci = float(pci); agari = float(agari); dist = int(dist)
    except: return None
    if math.isnan(pci) or math.isnan(agari): return None
    
    ave3f = (pci + 50) * agari / 100      # 前半3F換算タイム
    front_1f = ave3f / 3                   # 前半1F平均
    
    # 距離別の基準値（最近傍距離を使用）
    dists = sorted(FRONT_PACE_BASE.keys())
    nearest = min(dists, key=lambda d: abs(d - dist))
    base_1f, std_1f = FRONT_PACE_BASE[nearest]
    std_1f = std_1f if std_1f > 0 else 0.2
    
    # Z = (基準 - 実際) / std  → マイナスが速い
    return round((base_1f - front_1f) / std_1f, 3)


def calc_pci_cs(past_runs, target_front_1f, tolerance_good=0.15, tolerance_near=0.30):
    """
    PCI追走スコア（PCI Chasing Score）

    各馬の過去走PCIから前半1F平均を逆算し、
    ターゲット前半速度（逃げ馬が作るペース）への対応実績を評価する。

    Args:
        past_runs:        過去走データのリスト（run_dataのdict）
        target_front_1f:  逃げ馬が作る想定前半1F平均（秒）
        tolerance_good:   「ほぼ同じ」とみなす誤差範囲（デフォルト±0.15秒）
        tolerance_near:   「近い」とみなす誤差範囲（デフォルト±0.30秒）

    Returns:
        dict: {
          'score':      PCI-CS スコア（プラス=追走能力高）,
          'judge':      '◎'/'○'/'△'/'×',
          'fastest_1f': 過去走での最速前半1F,
          'best_run':   最も速い前半で好走したレース名,
          'n_fast':     ターゲット以上の前半経験走数,
          'detail':     詳細文字列,
        }
    """
    valid_runs = []
    for r in past_runs:
        if r.get('excluded_baba') or r.get('excluded_track'):
            continue
        pci = r.get('pci')
        agari = r.get('agari')
        if pci is None or agari is None:
            continue
        try:
            pci_f = float(pci); agari_f = float(agari)
            if math.isnan(pci_f) or math.isnan(agari_f):
                continue
        except:
            continue
        # PCIから前半1F平均を逆算
        ave3f = (pci_f + 50) * agari_f / 100
        front_1f = ave3f / 3
        valid_runs.append({
            'race':     r.get('race', ''),
            'front_1f': front_1f,
            'rank':     r.get('rank_int'),
            'agari':    agari_f,
            'pci':      pci_f,
        })

    if not valid_runs:
        return {'score': 0.0, 'judge': '△', 'fastest_1f': None,
                'best_run': None, 'n_fast': 0, 'detail': 'PCIデータなし'}

    score = 0.0
    best_run = None
    detail_parts = []

    for r in valid_runs:
        diff = target_front_1f - r['front_1f']  # プラス=ターゲット以上の前半経験
        rank = r['rank']

        if diff >= 0:  # ターゲット以上に速い前半を経験済み
            if rank and rank <= 3:
                s = min(3.0, diff * 10 + 2.0)
                score += s
                if best_run is None or r['front_1f'] < best_run['front_1f']:
                    best_run = r
                mark = '✅'
            elif rank and rank <= 6:
                score += min(1.0, diff * 5) * 0.3
                mark = '△'
            else:
                score -= 0.5  # 速いペースで大敗
                mark = '❌'
            detail_parts.append(f'{r["race"][:8]}(1F={r["front_1f"]:.3f},{rank}着{mark})')

        elif diff >= -tolerance_good:  # ほぼ同じ速度
            if rank and rank <= 3:
                score += 1.0
                mark = '✅近'
            elif rank and rank <= 6:
                score += 0.2
                mark = '△近'
            else:
                mark = ''
            if mark:
                detail_parts.append(f'{r["race"][:8]}(1F={r["front_1f"]:.3f},{rank}着{mark})')

        elif diff >= -tolerance_near:  # やや遅い前半
            if rank and rank <= 3:
                score += 0.3

    # 速い前半経験が全くない場合はペナルティ
    fastest = min(r['front_1f'] for r in valid_runs)
    n_fast  = sum(1 for r in valid_runs if r['front_1f'] <= target_front_1f + tolerance_good)
    if fastest > target_front_1f + tolerance_near:
        score -= 1.5
        detail_parts.append(f'最速前半={fastest:.3f}秒/F（経験不足）')

    score = round(score, 2)
    if score >= 2.0:   judge = '◎'
    elif score >= 0.5: judge = '○'
    elif score >= -0.5: judge = '△'
    else:              judge = '×'

    detail = ' / '.join(detail_parts[:3]) if detail_parts else f'最速={fastest:.3f}秒/F'
    best_name = best_run['race'][:10] if best_run else None

    return {
        'score':      score,
        'judge':      judge,
        'fastest_1f': round(fastest, 3),
        'best_run':   best_name,
        'n_fast':     n_fast,
        'detail':     detail,
    }


def is_1200m_bakuketsu_zone(race_dist):
    """
    1200m戦の爆穴ゾーン判定。

    検証結果（2020-2026年G1/G2/G3、554件）:
      1200m戦で10人気以下の馬を単勝で買うと回収率132.4%（全体平均73.3%より高い）
      G1のみ40.3%・3歳限定戦のみ23.2%と、世間の注目度や世代の壁は
      むしろ「的確な評価」につながり爆穴が出にくい方向に働く一方、
      1200mは前半3F・後半3Fのみで決着するためレース内容が単純で、
      展開や相手関係の「読み」が他距離より効きやすいと考えられる。
      LPI上位×1200m×人気10位以下の複合では47件で回収率128.7%（条件なしの67.8%より高い）。

    Returns: bool（1200m前後＝爆穴が出やすい距離帯ならTrue）
    """
    try:
        return abs(float(race_dist) - 1200) <= 100
    except Exception:
        return False


def calc_race_env_score(rpci, dist, grade, venue):
    """
    「今回出走するレース」自体の紛れやすさを判定する（calc_chase_env_discountの逆方向用）。

    検証結果（2024-2025年G1/G2/G3・816件 vs 207件、95%CI±3.1%/±6.2%）:
      env_score<=1（紛れにくい: 少頭数寄り・Sペース寄り・マイル以上・G1/G2・主要場）
        × LPI1-5位 → 複勝率29.5%・単勝回収率98.4%
      env_score>=2（紛れやすい）× LPI1-5位 → 複勝率29.5%・単勝回収率66.1%
    複勝率は同水準だが、紛れにくい環境の方が回収率が明確に高い。
    そのため「堅実軸」は env_score<=1 のレースでのLPI上位馬とする。

    Returns: int (0〜4, 高いほど紛れやすい)
    """
    score = 0
    try:
        if rpci is not None and float(rpci) <= 47: score += 1
    except Exception:
        pass
    try:
        if dist is not None and float(dist) <= 1400: score += 1
    except Exception:
        pass
    if grade == 'G3': score += 1
    if venue in ('函館', '新潟', '小倉'): score += 1
    return score


def calc_chase_env_discount(rpci, dist, grade, venue):
    """
    レース環境スコア（紛れの起きやすさ）からZへの割引係数を返す。

    背景: 馬個体の過去成績パターンでは爆穴（人気薄の3着以内）を判別できなかったが、
    「レース環境」側（出走頭数・ペース・距離・グレード・開催地）には明確な判別力があった。
    Hペース・短距離・G3・小場開催のレースほど「紛れ」が起きやすく、
    そこでの好走は次走での再現率が約15%低い（2020-2026年G1/G2/G3・740レース検証）。
    そのため、こうした環境下での好走（Z）はそのまま信用せず、軽く割り引いて評価する。

    出走頭数・先行馬数は出走表に無いため、ここではRPCI・距離・グレード・開催地のみで判定する
    （簡易版でも0点→22.3%、2点→43.5%の単調な判別力を確認済み）。

    Returns: 0.70〜1.00のZ割引係数（1.00=割引なし）
    """
    score = 0
    try:
        if rpci is not None and float(rpci) <= 47: score += 1   # Hペース（紛れやすい）
    except Exception:
        pass
    try:
        if dist is not None and float(dist) <= 1400: score += 1  # 短距離
    except Exception:
        pass
    if grade == 'G3': score += 1
    if venue in ('函館', '新潟', '小倉'): score += 1

    if score <= 0:   return 1.00
    elif score == 1: return 0.90
    elif score == 2: return 0.80
    else:            return 0.70


def calc_course_weight(run_dist, run_venue, target_dist, target_venue):
    """
    過去走のコース・距離と今回の一致度から重みを計算。

    設計根拠:
    - 同コース・同距離が最も信頼性が高い（重み3.0）
    - 距離差が大きいほど重みが下がる
    - 他コースは同距離でも重み1.2（コース特性の差）
    - 他コース・遠距離は重み0.3（参考程度）

    例（対阪神2200m）:
      阪神2200m → 3.0  阪神2000m → 1.5  東京2400m → 0.8
      中山2200m → 1.2  東京2000m → 0.8  中山2500m → 0.5
    """
    try:
        run_dist    = float(run_dist)
        target_dist = float(target_dist)
        same_venue  = str(run_venue) == str(target_venue)
        dist_diff   = abs(run_dist - target_dist)
    except Exception:
        return 1.0

    if same_venue and dist_diff == 0:     return 3.0
    elif same_venue and dist_diff <= 200: return 2.0
    elif same_venue and dist_diff <= 600: return 1.5
    elif dist_diff == 0:                  return 1.2
    elif dist_diff <= 200:                return 0.8
    elif dist_diff <= 400:                return 0.5
    else:                                 return 0.3

WALK_DEFS = [
    {'n':1,'agari':'上り3F',  'rpci':'RPCI',  'venue':'場所',  'dist':'距離',
     'baba':'馬場状態',  'rank':'着順',  'race':'ﾚｰｽ名･1走前','td':'TD','gap':'-3F差'},
    {'n':2,'agari':'上り3F.1','rpci':'RPCI.1','pci':'PCI.1','venue':'場所.1','dist':'距離.1',
     'baba':'馬場状態.1','rank':'着順.1','race':'ﾚｰｽ名･2走前','td':'TD.1','gap':'-3F差.1'},
    {'n':3,'agari':'上り3F.2','rpci':'RPCI.2','pci':'PCI.2','venue':'場所.2','dist':'距離.2',
     'baba':'馬場状態.2','rank':'着順.2','race':'ﾚｰｽ名･3走前','td':'TD.2','gap':'-3F差.2'},
    {'n':4,'agari':'上り3F.3','rpci':'RPCI.3','pci':'PCI.3','venue':'場所.3','dist':'距離.3',
     'baba':'馬場状態.3','rank':'着順.3','race':'ﾚｰｽ名･4走前','td':'TD.3','gap':'-3F差.3'},
    {'n':5,'agari':'上り3F.4','rpci':'RPCI.4','pci':'PCI.4','venue':'場所.4','dist':'距離.4',
     'baba':'馬場状態.4','rank':'着順.4','race':'ﾚｰｽ名･5走前','td':'TD.4','gap':'-3F差.4'},
]

ELEM_COLOR = {
    '基礎スピード・パワー': '#e8a030',
    'パワー・ロンスパ':     '#E24B4A',
    'ロンスパ・ギアチェンジ':'#378ADD',
    'ギアチェンジ':         '#639922',
    'ロンスパ':             '#888780',
    '不明':                 '#aaa',
}

# ============================================================
# ユーティリティ関数（変更不要）
# ============================================================
def sigmoid_score(r):
    z = (r - SIGMOID_CENTER) / SIGMOID_SCALE
    s = 1 / (1 + math.exp(-max(-10, min(10, z))))
    return round(40 + s * 60, 1)

def extract_grade(n):
    m = re.search(r'G[1-3]', str(n))
    return m.group() if m else ('L' if 'L' in str(n) else '')

def to_int_rank(s):
    try:
        return int(str(s).translate(str.maketrans('１２３４５６７８９０','1234567890')))
    except:
        return None

def get_venue_from_kaisan(s):
    kanji = re.sub(r'[0-9０-９A-Za-zａ-ｚＡ-Ｚ]', '', str(s).strip())
    VMAP = {
        '東京':'東京','中山':'中山','京都':'京都','阪神':'阪神','新潟':'新潟',
        '中京':'中京','福島':'福島','小倉':'小倉','札幌':'札幌','函館':'函館',
        '東':'東京','京':'京都','阪':'阪神','新':'新潟','札':'札幌',
        '函':'函館','小':'小倉','福':'福島','中':'中山','名':'中京',
    }
    return VMAP.get(kanji.strip(), '東京')

def get_std_weight(grade, age, sex):
    key = (grade, '3yo' if age == 3 else 'senior')
    if key not in WEIGHT_TABLE:
        key = ('', key[1])
    p = WEIGHT_TABLE[key]
    return p[1] if sex == '牝' else p[0]

def weight_correction_sec(grade, age, sex):
    return (WEIGHT_BASE - get_std_weight(grade, age, sex)) * WEIGHT_PER_KG

def classify_element(rpci, gap_est, z=0.0):
    if rpci is None or gap_est is None:
        return '不明'
    try:
        if math.isnan(float(rpci)) or math.isnan(float(gap_est)):
            return '不明'
    except:
        return '不明'
    rpci, gap_est = float(rpci), float(gap_est)
    is_後傾 = rpci >= 50
    is_先行 = gap_est < 0.6
    is_速   = float(z) > 0.3
    if is_後傾:
        if not is_先行: return 'ギアチェンジ' if is_速 else 'ロンスパ'
        else:           return 'ロンスパ・ギアチェンジ' if is_速 else '基礎スピード・パワー'
    else:
        if is_先行: return '基礎スピード・パワー'
        else:       return 'パワー・ロンスパ'

def calc_pb_v11(rpci, gap_est, z):
    rpci_dev = abs(rpci - 50) / 10
    is_後傾  = rpci >= 50
    is_先行  = gap_est < 0.6
    is_差し  = gap_est >= 0.8
    adj = 0.0
    if   is_後傾 and is_先行: adj = -rpci_dev * (0.6 - gap_est) / 0.6 * 0.4
    elif is_後傾 and is_差し: adj =  rpci_dev * (gap_est - 0.8) / 0.4 * 0.3
    elif not is_後傾 and is_先行: adj = rpci_dev * (0.6 - gap_est) / 0.6 * 0.3
    elif not is_後傾 and is_差し: adj = -rpci_dev * (gap_est - 0.8) / 0.4 * 0.4
    if adj > 0:   adj *= max(0.3, min(2.0, 1.0 + z * 0.3))
    elif adj < 0 and z > 0.5: adj += min(abs(adj) * 0.5, z * 0.1)
    return round(adj, 3)

def get_venue_bonus(venue, elem):
    return VENUE_ELEMENT_COEF.get(venue, {}).get(elem, 1.0)

def apply_venue_bonus(venue, elem, lpi, strength=0.15):
    coef  = get_venue_bonus(venue, elem)
    delta = (coef - 1.0) * strength * 100
    return max(40.0, min(100.0, round(lpi + delta, 1)))

# ============================================================
# 基準テーブル構築（キャッシュ）
# ============================================================
@st.cache_data
def build_base_table(file_bytes):
    # エンコードを自動判定
    for enc in ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        raise ValueError('CSVの文字コードを判定できませんでした')

    df['距離_num'] = df['距離'].str.extract(r'(\d+)').astype(float)
    df['上がり']   = pd.to_numeric(df['上り3F'], errors='coerce')
    df['競馬場']   = df['開催'].apply(get_venue_from_kaisan)
    df['馬場']     = df['馬場状態'].str.strip()
    df['日付_num'] = pd.to_numeric(df['日付'], errors='coerce')
    df['年']       = (df['日付_num'] // 10000).fillna(0).astype(int)
    df['レース名_s'] = df['レース名'].str.strip() if 'レース名' in df.columns else ''

    # ===== 年度重み（直近ほど重い）=====
    def yr_weight(y):
        try: y = int(y)
        except: return 1.0
        return 2.0 if y >= 25 else (1.5 if y >= 23 else 1.0)
    df['yr_w'] = df['年'].apply(yr_weight)

    valid = df[df['馬場'].isin(['良', '稍'])].copy()

    # 年度重み付き平均・std
    def weighted_stats(g):
        v = g.dropna(subset=['上がり'])
        if len(v) == 0:
            return pd.Series({'avg': np.nan, 'std': np.nan, 'n': 0})
        w = v['yr_w']
        wsum = w.sum()
        wavg = (v['上がり'] * w).sum() / wsum
        wvar = (w * (v['上がり'] - wavg) ** 2).sum() / wsum
        return pd.Series({'avg': wavg, 'std': max(np.sqrt(wvar), 0.3), 'n': len(v)})

    stats = valid.groupby(['距離_num', '競馬場', '馬場']).apply(weighted_stats).reset_index()
    stats = stats[stats['n'] >= 5]
    良_s  = stats[stats['馬場'] == '良']
    稍_s  = stats[stats['馬場'] == '稍']
    base_dict = {(r['距離_num'], r['競馬場']): (r['avg'], r['std']) for _, r in 良_s.iterrows()}
    稍重_dict = {(r['距離_num'], r['競馬場']): (r['avg'], r['std']) for _, r in 稍_s.iterrows()}

    # ===== 同名レース＋直近重み付き基準辞書 =====
    def normalize_name(n):
        return re.sub(r'[ＨＧＳＬ０-９G0-9HLS\s\u3000・Ｐ]', '', str(n))

    race_base_dict = {}
    vg = valid[valid['馬場'] == '良'].copy()
    if len(vg) > 0 and '日付_num' in vg.columns:
        race_avgs = vg.groupby(
            ['距離_num', '競馬場', '日付_num', 'レース名_s', '年']
        )['上がり'].agg(avg='mean', n='count').reset_index()
        race_avgs = race_avgs[race_avgs['n'] >= 5]

        for (dist, venue), grp in race_avgs.groupby(['距離_num', '競馬場']):
            grp = grp.sort_values('日付_num', ascending=False).reset_index(drop=True)
            seen = set()
            for _, row in grp.iterrows():
                tname = normalize_name(row['レース名_s'])
                if not tname or len(tname) < 2 or tname in seen:
                    continue
                seen.add(tname)

                w_rows = []
                for idx2, row2 in grp.iterrows():
                    rname2 = normalize_name(row2['レース名_s'])
                    yr_w2  = yr_weight(row2['年'])
                    # 同名ボーナス
                    if tname == rname2:
                        name_w = 3.0
                    elif len(tname) >= 3 and (tname[:3] in rname2 or rname2[:3] in tname):
                        name_w = 2.0
                    else:
                        name_w = 1.0
                    recency_w = max(0.3, 1.0 - idx2 * 0.08)
                    w_rows.append((row2['avg'], yr_w2 * name_w * recency_w))

                # 同名全件＋直近5件（他）
                same  = [(a, w) for i, (a, w) in enumerate(w_rows)
                         if normalize_name(grp.iloc[i]['レース名_s'])[:3] == tname[:3]]
                other = [(a, w) for i, (a, w) in enumerate(w_rows)
                         if normalize_name(grp.iloc[i]['レース名_s'])[:3] != tname[:3]][:5]
                use = same + other
                total_w = sum(w for _, w in use)
                if total_w == 0:
                    continue
                wavg = sum(a * w for a, w in use) / total_w
                race_base_dict[(float(dist), str(venue), tname)] = round(wavg, 3)

    return base_dict, 稍重_dict, race_base_dict

def get_z(agari, dist, venue, baba, base_dict, 稍重_dict,
          race_base=None, race_name=None):
    """
    Zスコア計算。race_base（同名レース重み付き基準）があれば優先使用。
    """
    fb  = {1000:32.5,1200:34.0,1400:34.2,1600:34.4,
           1800:34.6,2000:35.0,2200:35.2,2400:35.3,2500:35.5}
    key = (float(dist), venue)
    b   = str(baba).strip()

    # 同名レース重み付き基準（良馬場のみ）
    if race_base and race_name and b == '良':
        tname = re.sub(r'[ＨＧＳＬOP０-９G0-9HLS\s\u3000・]','',str(race_name))
        rkey  = (float(dist), venue, tname)
        if rkey in race_base:
            base = race_base[rkey]
            # stdは通常の基準テーブルから取得
            _, std = base_dict.get(key, (base, 1.0))
            std = std if (std and std > 0) else 1.0
            return (base - agari) / std

    if b == '稍' and key in 稍重_dict:
        base, std = 稍重_dict[key]
    elif key in base_dict:
        base, std = base_dict[key]
        if b == '重': base += 0.8
        elif b == '不': base += 1.5
    else:
        base, std = fb.get(int(dist), 34.4), 1.0
    std = std if (std and std > 0) else 1.0
    return (base - agari) / std

# ============================================================
# 1200m専用AI（既存LPIロジックとは独立した専用モデル）
# ============================================================
def calc_lpi_1200m(entry_bytes, base_dict, 稍重_dict,
                    target_venue='中京', target_grade='G3',
                    senkou_bonus_weight=0.3, rank_weight=0.4, kakuwami_penalty=1.0):
    """
    1200m戦専用のLPI計算。

    設計思想:
    1200m戦は前半3F・後半3Fのみで完結する単純な構造のため、
    「1200mでの実績」が他距離の実績より強く次走の結果に結びつく。
    既存のcalc_lpi（G1好走ボーナス・連勝ボーナス・環境割引・会場補正など
    複数の補正が積み重なった汎用モデル）とは独立させ、
    「過去走を1200m限定走に絞り込んだZの加重平均」+
    「先行好走ボーナス」+「着順加点」+「格上挑戦ペナルティ」の
    4要素だけで評価する。

    検証結果（2023-2025年G1/G2/G3、33レース、3頭ボックス馬連）:
      2023年: 11レース中2的中(18.2%) 回収率152.1%
      2024年: 11レース中4的中(36.4%) 回収率799.1%（大穴1件含む）
      2025年: 11レース中2的中(18.2%) 回収率147.6%
      2026年: 5レース中0的中（サンプル不足、要継続観察）
    複雑な補正を重ねたcalc_lpi本体では同等の効果が再現しなかったため、
    1200m専用に切り出した独立関数として実装している。

    格上挑戦ペナルティ（追加）:
    過去5走の最高グレードより今回のグレードが上の場合（例: 過去最高G3→今回G1）、
    Zから一律ペナルティを引く。2023-2025年・517件の検証で、格上挑戦の馬は
    好走率(3着以内)19.6%→11.1%、大敗率(10着以下)42.1%→58.6%という
    明確な判別力を確認済み。高松宮記念2025のペアポルックス（過去最高G3
    オーシャンS2着等→G1で18着大敗）のような過大評価を防ぐ。
    全体の的中率・回収率への影響は小さく、安全に追加できる。

    Returns: list of dict（calc_lpiと互換のキーを持つ簡易結果）
    """
    GRADE_RANK = {'G1': 4, 'G2': 3, 'G3': 2, 'L': 1, '': 0}
    target_grade_rank = GRADE_RANK.get(target_grade, 0)

    for enc in ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']:
        try:
            df = pd.read_csv(io.BytesIO(entry_bytes), encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        raise ValueError('出走表CSVの文字コードを判定できませんでした')

    results = []
    for _, row in df.iterrows():
        horse = str(row['馬名S'])
        all_runs = []

        for wd in WALK_DEFS:
            try:
                agari_raw = str(row[wd['agari']]).strip()
                if agari_raw in ['----', '---', '', 'nan']: continue
                agari = float(agari_raw)
                venue = FULL_VENUE.get(str(row[wd['venue']]).strip(), '東京')
                dist  = float(str(row[wd['dist']]).strip().replace('m', '').replace('芝', '').replace('ダ', ''))
                baba  = str(row[wd['baba']]).strip()
                baba  = baba if baba not in ['nan', 'NaN', ''] else '良'
                rank  = row[wd['rank']]
                race  = str(row[wd['race']]).strip()
                td    = str(row.get(wd['td'], 'T')).strip().upper()
                track = td if td in ('T', 'D') else 'T'
                gap_raw = row.get(wd['gap'], None)
                gap   = float(gap_raw) if str(gap_raw).strip() not in ['nan', 'NaN', '', 'None', '----'] else None
            except Exception:
                continue
            if math.isnan(agari): continue
            if track != 'T' or baba not in ('良', '稍'): continue

            rank_int = to_int_rank(rank)
            grade    = extract_grade(race)
            z = get_z(agari, dist, venue, baba, base_dict, 稍重_dict, None, race)
            gap_est = gap if (gap is not None and not math.isnan(gap)) else 1.5
            gw = GRADE_WEIGHT.get(grade, GRADE_WEIGHT[''])

            all_runs.append({
                'race': race, 'dist': dist, 'venue': venue, 'z': z,
                'rank_int': rank_int, 'gap_est': gap_est, 'grade_weight': gw,
                'grade': grade,
            })

        if not all_runs:
            continue

        # 格上挑戦判定: 過去5走（距離問わず全履歴）の最高グレードより今回が上か
        max_past_grade = max((GRADE_RANK.get(r['grade'], 0) for r in all_runs[:5]), default=0)
        is_kakuwami = target_grade_rank > max_past_grade

        # 1200m限定走への絞り込み（2走未満なら全距離で補完）
        runs_1200 = [r for r in all_runs if abs(r['dist'] - 1200) <= 50]
        use = runs_1200 if len(runs_1200) >= 2 else all_runs
        use = use[:5]

        tw = sum(r['grade_weight'] for r in use)
        z_avg = sum(r['z'] * r['grade_weight'] for r in use) / tw if tw > 0 else np.mean([r['z'] for r in use])

        # 先行好走ボーナス: 先行(地点差<=0.4)かつ3着以内だった回数
        n_senkou_win = sum(1 for r in use if r['gap_est'] <= 0.4 and r['rank_int'] and r['rank_int'] <= 3)
        senkou_bonus = min(n_senkou_win * senkou_bonus_weight, senkou_bonus_weight * 3)

        # 着順加点: 1着=3点/2着=2点/3着=1点（グレード重み付き）
        rank_scores = [max(0, 4 - r['rank_int']) * r['grade_weight']
                       for r in use if r['rank_int'] and r['rank_int'] <= 3]
        rank_bonus = round(sum(rank_scores) / tw * rank_weight, 3) if tw > 0 and rank_scores else 0.0

        z_final = z_avg + senkou_bonus + rank_bonus
        if is_kakuwami:
            z_final -= kakuwami_penalty

        lpi = sigmoid_score(z_final)
        lpi_venue = apply_venue_bonus(target_venue, '不明', lpi, 0.15)

        results.append({
            'horse': horse,
            'avg_lpi': round(lpi, 1),
            'avg_venue_lpi': round(lpi_venue, 1),
            'z_final': round(z_final, 3),
            'z_avg': round(z_avg, 3),
            'senkou_bonus': round(senkou_bonus, 2),
            'rank_bonus': round(rank_bonus, 2),
            'is_kakuwami': is_kakuwami,
            'n_senkou_win': n_senkou_win,
            'n_runs_used': len(use),
            'used_1200m_only': len(runs_1200) >= 2,
        })

    return results

# ============================================================
# LPI計算メイン
# ============================================================
def calc_lpi(entry_bytes, base_dict, 稍重_dict,
             target_track='T', target_venue='東京', bonus_strength=0.15,
             pace_pred_rpci=51.0, race_base_dict=None, target_race_name='',
             target_front_1f_input=None, cushion_correction_input=0.0):
    for enc in ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']:
        try:
            df = pd.read_csv(io.BytesIO(entry_bytes), encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        raise ValueError('出走表CSVの文字コードを判定できませんでした')

    sex_map = {}
    age_map = {}
    if '性別' in df.columns:
        for _, row in df.iterrows():
            sex_map[str(row['馬名S'])] = str(row['性別']).strip()
    if '年齢' in df.columns:
        for _, row in df.iterrows():
            try:    age_map[str(row['馬名S'])] = int(row['年齢'])
            except: age_map[str(row['馬名S'])] = 4

    results = []
    for _, row in df.iterrows():
        horse = str(row['馬名S'])
        sex   = sex_map.get(horse, '牡')
        age   = age_map.get(horse, 4)
        run_data = []

        for wd in WALK_DEFS:
            try:
                agari_raw = str(row[wd['agari']]).strip()
                if agari_raw in ['----','---','','nan']: continue
                agari = float(agari_raw)
                rpci_raw = str(row[wd['rpci']]).strip()
                if rpci_raw in ['','nan','NaN']: continue
                rpci  = float(rpci_raw)
                venue = FULL_VENUE.get(str(row[wd['venue']]).strip(), '東京')
                dist  = float(str(row[wd['dist']]).strip().replace('m','').replace('芝','').replace('ダ',''))
                baba  = str(row[wd['baba']]).strip()
                baba  = baba if baba not in ['nan','NaN',''] else '良'
                rank  = row[wd['rank']]
                race  = str(row[wd['race']]).strip()
                td    = str(row.get(wd['td'], 'T')).strip().upper()
                track = td if td in ('T','D') else 'T'
                gap_raw = row.get(wd['gap'], None)
                gap   = float(gap_raw) if str(gap_raw).strip() not in ['nan','NaN','','None','----'] else None
                pci_raw = row.get(wd.get('pci',''), None)
                pci_val = float(str(pci_raw).strip()) if str(pci_raw).strip() not in ['nan','NaN','','None','----'] else None
            except:
                continue
            if math.isnan(agari) or math.isnan(rpci): continue

            gap_est  = gap if (gap is not None and not math.isnan(gap)) else 1.5
            grade    = extract_grade(race)
            wt_corr  = weight_correction_sec(grade, age, sex)
            agari_adj = agari + wt_corr
            z        = get_z(agari_adj, dist, venue, baba, base_dict, 稍重_dict, race_base_dict, race)
            pb       = calc_pb_v11(rpci, gap_est, z)
            pm       = 1.0 + abs(rpci - 50) / 25 * 0.4
            rank_int = to_int_rank(rank)

            g1_pen = 1.0
            if grade == 'G1' and rank_int and rank_int > 3 and gap_est > G1_PENALTY_THRESHOLD:
                g1_pen = G1_PENALTY_COEF

            hb, hb_r = 0.0, ''
            if rank_int and rank_int <= 3:
                is_先行_b = gap_est <= 0.4
                is_差し_b = gap_est >= 0.8
                base_b = 0.0
                if rpci <= 50 and is_先行_b:
                    base_b = min((50-rpci)/10*(0.4-gap_est+0.1)*2*0.8, 1.5)
                    hb_r   = f'前傾×先行{rank_int}着[{grade}]'
                elif rpci > 50 and is_差し_b:
                    base_b = min((rpci-50)/10*(gap_est-0.8+0.1)*2*0.8, 1.5)
                    hb_r   = f'後傾×差し{rank_int}着[{grade}]'
                if base_b > 0:
                    if z > 0.5: base_b *= 1.2; hb_r += ' +速上がり'
                    base_b *= GRADE_BONUS.get(grade, 0.7)
                    base_b *= RANK_BONUS_MULT.get(rank_int, 1.0)
                    hb = round(min(base_b, 2.5), 3)

            elem = classify_element(rpci, gap_est, z)

            # 環境スコア割引: 紛れが起きやすいレース環境での好走（高Z）を軽く割り引く
            # rank_int<=3（好走）でZ>0（平均以上の上がり）の場合のみ適用する
            # （凡走時は割引する意味がない。むしろ大敗の評価には影響させない）
            env_discount = 1.0
            if rank_int and rank_int <= 3 and z > 0:
                env_discount = calc_chase_env_discount(rpci, dist, grade, venue)
                z_for_lpi = z * env_discount
            else:
                z_for_lpi = z

            lpi  = sigmoid_score((z_for_lpi + pb + hb) * pm * g1_pen)
            gw   = GRADE_WEIGHT.get(grade, GRADE_WEIGHT[''])

            # 前半ペースZスコア（PCIから逆算）
            fp_z = calc_front_pace_z(pci_val, agari, dist) if pci_val is not None else None

            run_data.append({
                'n': wd['n'], 'race': race, 'dist': dist, 'venue': venue,
                'rpci': rpci, 'pci': pci_val, 'gap_est': round(gap_est, 2),
                'agari': agari, 'agari_adj': round(agari_adj, 2),
                'wt_corr': round(wt_corr, 2),
                'z': round(z_for_lpi, 3), 'z_raw': round(z, 3),
                'env_discount': env_discount,
                'rank': rank, 'rank_int': rank_int,
                'baba': baba, 'track': track, 'grade': grade,
                'pb': pb, 'pm': round(pm, 3), 'hb': hb, 'hb_r': hb_r,
                'elem': elem, 'lpi': lpi, 'grade_weight': gw,
                'front_pace_z': round(fp_z, 3) if fp_z is not None else None,
                'excluded_baba':  baba not in GOOD_BABA,
                'excluded_track': track != target_track,
            })

        if not run_data: continue
        valid = [r for r in run_data if not r['excluded_baba'] and not r['excluded_track']]
        use   = valid if valid else run_data

        # 改善③: 大敗（壊滅的なZの低下）が平均を過剰に押し下げないようキャップする。
        # 1走の極端な大敗（Z<Z_FLOOR）はLPI換算後の値をZ_FLOOR相当に制限し、
        # 好走実績が1度の大敗で相殺され過ぎないようにする。
        Z_FLOOR = -1.5
        LPI_FLOOR = sigmoid_score(Z_FLOOR)
        use = [
            {**r, 'lpi': max(r['lpi'], LPI_FLOOR)} if r['z'] < Z_FLOOR else r
            for r in use
        ]

        total_w = sum(r['grade_weight'] for r in use)
        avg_lpi = round(sum(r['lpi']*r['grade_weight'] for r in use)/total_w, 1) \
                  if total_w > 0 else round(np.mean([r['lpi'] for r in use]), 1)

        good     = [r for r in use if r['rank_int'] and r['rank_int'] <= 3]
        elem_src = good if good else use
        dom_elem = Counter([classify_element(r['rpci'], r['gap_est'], r['z'])
                            for r in elem_src]).most_common(1)[0][0] if elem_src else '不明'

        adj_lpis = [apply_venue_bonus(target_venue, r['elem'], r['lpi'], bonus_strength)
                    for r in use]
        tw = sum(r['grade_weight'] for r in use)
        avg_venue = round(sum(a*r['grade_weight'] for a,r in zip(adj_lpis, use))/tw, 1) \
                    if tw > 0 else round(np.mean(adj_lpis), 1)

        coef = get_venue_bonus(target_venue, dom_elem)

        # PCI追走スコア（逃げ馬ペースへの対応実績）
        pci_cs_result = None
        if pace_pred_rpci is not None:
            # サイドバーのtarget_front_1fは外から渡せないので
            # run_data に格納してUIで使う
            pass

        # ポジション予測（有効走の地点差から）
        past_gaps_for_pred = [r['gap_est'] for r in use
                               if r['gap_est'] < 5.0][:5]  # 大外れ値除外
        pos_pred = predict_position(past_gaps_for_pred, pace_pred_rpci)

        # 上がり予測（過去走のZスコアから）
        # コースのペース予測からペース帯を決定
        _pred_rpci = pace_pred_rpci
        _pace_cat  = 'H' if _pred_rpci <= 47 else ('S' if _pred_rpci >= 54 else 'M')

        # 予測ポジション（地点差）を上がり予測に渡す
        _pred_gap = pos_pred['pred_gap'] if pos_pred else None
        # PCI-CSスコアを上がり予測に渡す（target_front_1fが設定されている場合）
        _pci_cs_score = None
        if target_front_1f_input is not None and target_front_1f_input > 0:
            _cs = calc_pci_cs(use[:5], target_front_1f_input)
            _pci_cs_score = _cs['score'] if _cs else None

        agari_pred = predict_agari(
            past_runs           = use[:5],
            target_dist         = float(str(run_data[0]['dist']).replace('m','')),
            target_venue        = target_venue,
            target_baba         = '良',
            predicted_pace_cat  = _pace_cat,
            pred_gap            = _pred_gap,
            pci_cs_score        = _pci_cs_score,
            cushion_correction  = cushion_correction_input,
            base_dict_for_z     = base_dict,
            pace_target_front_1f= target_front_1f_input,
        )

        # ===== 好走LPIボーナス（全グレード対応・直近5走対応）=====
        # 改善①: G1限定だった対象をG1/G2/G3/Lの全グレードに拡張し、直近5走全てを対象にする。
        #         着順1着の馬の評価を「Zの加重平均」だけに任せず、勝ち切った実績を直接加点する。
        # グレード別・着順別ボーナステーブル（1着が最大、3着まで対象）
        GRADE_RANK_BONUS_TABLE = {
            'G1': {1: 3.0, 2: 2.0, 3: 1.0},
            'G2': {1: 2.0, 2: 1.3, 3: 0.7},
            'G3': {1: 1.5, 2: 1.0, 3: 0.5},
            'L':  {1: 1.0, 2: 0.6, 3: 0.3},
        }
        g1_lpi_bonus = 0.0
        g1_bonus_detail = []
        for rn in run_data[:5]:   # 直近5走全てを対象
            grade = rn['grade']
            if grade not in GRADE_RANK_BONUS_TABLE:
                continue
            if rn['rank_int'] and rn['rank_int'] <= 3:
                b = GRADE_RANK_BONUS_TABLE[grade].get(rn['rank_int'], 0)
                if b > 0:
                    g1_lpi_bonus += b
                    g1_bonus_detail.append(f"{rn['race']}_{rn['rank_int']}着+{b}")
        g1_lpi_bonus = min(g1_lpi_bonus, 8.0)   # 上限8点（5走対応で上限を拡張）

        # 改善②: 連続好走（直近2走以上連続で3着以内）への追加ボーナス
        # サトノレーヴ（1着→1着→1着）のような「勢いのある馬」を正当評価する。
        streak_bonus = 0.0
        streak_detail = ''
        streak_len = 0
        for rn in run_data[:5]:
            if rn['rank_int'] and rn['rank_int'] <= 3:
                streak_len += 1
            else:
                break
        if streak_len >= 2:
            # 2連続+1.0、3連続+2.0、4連続+3.0、5連続+4.0（上限4.0）
            streak_bonus = min((streak_len - 1) * 1.0, 4.0)
            streak_detail = f'直近{streak_len}走連続3着以内+{streak_bonus:.1f}'
        g1_lpi_bonus = min(g1_lpi_bonus + streak_bonus, 10.0)
        if streak_detail:
            g1_bonus_detail.append(streak_detail)

        # ボーナスをLPIに加算（上限100）
        avg_lpi_adj      = min(100.0, round(avg_lpi      + g1_lpi_bonus, 1))
        avg_venue_lpi_adj = min(100.0, round(avg_venue   + g1_lpi_bonus, 1))

        results.append({
            'horse': horse, 'sex': sex, 'age': age,
            'avg_lpi': avg_lpi_adj, 'avg_venue_lpi': avg_venue_lpi_adj,
            'avg_lpi_raw': avg_lpi, 'avg_venue_raw': avg_venue,
            'g1_lpi_bonus': round(g1_lpi_bonus, 1),
            'g1_bonus_detail': ' / '.join(g1_bonus_detail),
            'max_lpi': round(max(r['lpi'] for r in run_data), 1),
            'latest_lpi': run_data[0]['lpi'],
            'n_valid': len(valid), 'n_total': len(run_data), 'n_good': len(good),
            'dom_elem': dom_elem, 'coef': round(coef, 2),
            'venue_delta': round(avg_venue - avg_lpi, 1),
            'pos_pred':   pos_pred,
            'agari_pred': agari_pred,
            'runs': run_data, 'valid_runs': valid, 'good_runs': good,
            'pci_cs_runs': use[:5],  # PCI-CS計算用の有効走
        })

    results.sort(key=lambda x: -x['avg_venue_lpi'])
    return results

# ============================================================
# グラフ描画
# ============================================================
def plot_ranking(results, race_name, target_venue):
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    # 日本語フォントを環境に応じて自動選択
    import matplotlib.font_manager as fm
    jp_fonts = ['Noto Sans CJK JP','IPAexGothic','IPAPGothic',
                'Hiragino Sans','Yu Gothic','Meiryo','MS Gothic']
    available = {f.name for f in fm.fontManager.ttflist}
    chosen = next((f for f in jp_fonts if f in available), None)
    if chosen:
        matplotlib.rcParams['font.family'] = chosen
    else:
        matplotlib.rcParams['font.family'] = 'DejaVu Sans'
    matplotlib.rcParams['axes.unicode_minus'] = False

    names   = [r['horse'] for r in results]
    avgs_v  = [r['avg_venue_lpi'] for r in results]
    avgs_b  = [r['avg_lpi'] for r in results]
    elems   = [r['dom_elem'] for r in results]
    n = len(names)

    colors = [ELEM_COLOR.get(e, '#888') for e in elems]
    fig, ax = plt.subplots(figsize=(10, max(5, n * 0.45 + 1.5)))

    y = list(range(n))
    ax.barh(y, avgs_b,  color='#e0e0e0', edgecolor='none', height=0.65, label='基本LPI')
    ax.barh(y, avgs_v,  color=colors,    edgecolor='none', height=0.42,
            alpha=0.92, label=f'{target_venue}補正LPI')
    ax.axvline(80, color='#E24B4A', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_yticks(y)
    # 日本語フォントが見つからない場合は順位番号のみ表示
    if chosen:
        ax.set_yticklabels([f'{i+1}. {n}' for i,n in enumerate(names)], fontsize=9)
    else:
        ax.set_yticklabels([f'{i+1}.' for i in range(len(names))], fontsize=9)
        # 代わりにグラフ右に馬名テキストを追加
        for i, name in enumerate(names):
            ax.text(56.5, i, name, va='center', fontsize=7,
                    color='gray', fontfamily='DejaVu Sans')
    ax.set_xlabel('LPI スコア', fontsize=10)
    ax.set_xlim(55, 96)
    ax.set_title(f'{race_name}  [{target_venue}適合補正]  LPI v11', fontsize=12, fontweight='bold')
    ax.grid(axis='x', alpha=0.2)

    for bar, val, dval in zip(
        ax.patches[n:],
        avgs_v,
        [v-b for v,b in zip(avgs_v, avgs_b)]
    ):
        sign = '+' if dval >= 0 else ''
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{val:.1f} ({sign}{dval:.1f})',
                va='center', fontsize=8)

    patches = [mpatches.Patch(color=c, label=e) for e,c in ELEM_COLOR.items() if e != '不明']
    ax.legend(handles=patches, fontsize=7, loc='lower right', ncol=2)
    plt.tight_layout()
    return fig

# ============================================================
# Streamlit UI
# ============================================================
st.title('🏇 LPI v11 競馬予想ツール')
st.caption('LPI (ラップ強さ指数) v11 — 位置取り補正・グレード加重・斤量補正・競馬場適合ボーナス対応')

# ---- サイドバー ----
with st.sidebar:
    st.header('⚙️ 設定')

    st.subheader('① 基準テーブル用CSV')
    base_file = st.file_uploader(
        '2023〜2026年全距離重賞CSVをアップ',
        type='csv', key='base')
    if base_file:
        st.success(f'{base_file.name} 読み込み済み')

    st.subheader('② 出走表CSV')
    entry_file = st.file_uploader(
        '予想するレースの出走表CSVをアップ',
        type='csv', key='entry')

    st.subheader('③ レース設定')
    race_name    = st.text_input('レース名', value='2026 安田記念G1')
    target_venue = st.selectbox(
        '競馬場',
        ['東京','中山','京都','阪神','中京','新潟','福島','小倉','札幌','函館'])
    target_track = st.radio('トラック', ['T（芝）','D（ダート）'])
    track_code   = 'T' if target_track.startswith('T') else 'D'
    bonus_strength = st.slider(
        '競馬場ボーナス強度', 0.0, 0.30, 0.15, 0.05,
        help='0=ボーナスなし / 0.15=標準 / 0.30=強め')

    st.subheader('④ ペース予測（任意）')
    race_dist = st.number_input('レース距離（m）', min_value=1000, max_value=3600, value=1600, step=200)
    nige_count   = st.number_input('逃げ馬頭数', min_value=0, max_value=10, value=0, step=1,
                                   help='出走表の決め手=逃げの馬の頭数')
    senkou_count = st.number_input('先行馬頭数', min_value=0, max_value=16, value=0, step=1,
                                   help='出走表の決め手=先行の馬の頭数')

    st.markdown('**ペース直接指定（任意）**')
    st.markdown('**ペース直接指定（任意）**')
    manual_pace = st.radio(
        'ペース帯を選択',
        options=['自動推定（コース統計から）', '🔵 H（ハイ）', '🟢 M（ミドル）', '🟠 S（スロー）'],
        index=0,
        help='自動推定: コース統計+逃げ・先行頭数から計算\n'
             'H: 前半が速く先行馬が消耗する展開\n'
             'M: 平均的なペース\n'
             'S: 前半が遅く上がり勝負になる展開',
        horizontal=False,
    )
    # radio の選択を pace_cat と manual_rpci に変換
    if '自動' in manual_pace:
        manual_rpci = 0.0
    elif 'H' in manual_pace:
        manual_rpci = 45.0   # H帯の代表値
    elif 'M' in manual_pace:
        manual_rpci = 51.0   # M帯の代表値
    else:  # S
        manual_rpci = 57.0   # S帯の代表値

    st.subheader('⑤ PCI追走スコア（任意）')
    use_pci_cs = st.checkbox(
        '逃げ馬ペースへの追走能力を評価する',
        value=False,
        help='逃げ馬がいる場合、そのペースに対応できる馬を評価します'
    )
    if use_pci_cs:
        target_front_1f = st.number_input(
            '逃げ馬の想定前半1F（秒）',
            min_value=10.5, max_value=13.5, value=11.9, step=0.05,
            help='PCIから逆算: (PCI+50)×上がり/100/3\n'
                 '例) タバル宝塚2025実績=11.892秒/F\n'
                 '    大阪杯ペース目安=11.8秒/F'
        )
        st.caption(
            f'ターゲット{target_front_1f:.3f}秒/F以下の前半を経験した馬を高評価'
        )
    else:
        target_front_1f = None

    st.subheader('⑥ クッション値（任意）')
    use_cushion = st.checkbox(
        'クッション値で基準上がりを補正する',
        value=False,
        help='当日朝に発表されるクッション値を入力すると\n'
             '基準上がりが自動補正されます。\n'
             '基準: 9.0（補正なし）\n'
             '7.0（軟）→基準+0.30秒 / 11.0（硬）→基準-0.30秒'
    )
    if use_cushion:
        cushion_val = st.number_input(
            'クッション値',
            min_value=5.0, max_value=14.0, value=9.0, step=0.1,
            help='JRAが当日朝に発表。競馬場公式サイトで確認できます。'
        )
        cushion_adj = round((9.0 - cushion_val) * 0.15, 3)
        if cushion_adj > 0:
            st.caption(f'クッション値{cushion_val:.1f} → 基準上がり{cushion_adj:+.2f}秒（遅い馬場）')
        elif cushion_adj < 0:
            st.caption(f'クッション値{cushion_val:.1f} → 基準上がり{cushion_adj:+.2f}秒（速い馬場）')
        else:
            st.caption('クッション値9.0 → 補正なし（標準）')
    else:
        cushion_val  = 9.0
        cushion_adj  = 0.0

    run_btn = st.button('🔍 LPI計算実行', type='primary', use_container_width=True)

# ---- メインエリア ----
if not base_file:
    st.info('← サイドバーから基準テーブル用CSVをアップしてください（2023〜2026年全距離重賞データ）')
    st.stop()

if not entry_file:
    st.info('← サイドバーから出走表CSVをアップしてください')
    st.stop()

if run_btn or (base_file and entry_file):
    # ペース予測（manual_rpci が入力されていればそちらを優先）
    if manual_rpci > 0:
        _mr = manual_rpci
        if _mr <= 47:
            _label, _lamp = 'ハイペース（直接指定）', '🔵'
            _elem_adv = ['基礎スピード・パワー', 'パワー・ロンスパ']
            _comment  = 'H（ハイ）指定 — 前半速く先行馬が消耗。基礎スピード型・差し馬有利'
        elif _mr >= 54:
            _label, _lamp = 'スローペース（直接指定）', '🟠'
            _elem_adv = ['ギアチェンジ', 'ロンスパ・ギアチェンジ']
            _comment  = 'S（スロー）指定 — 上がり勝負。GC型有利、先行馬の前残りも警戒'
        else:
            _label, _lamp = 'ミドルペース（直接指定）', '🟢'
            _elem_adv = []
            _comment  = 'M（ミドル）指定 — 平均的なペース。どちらも起こりうる'
        pace = dict(pred_rpci=_mr, base_rpci=_mr, std=0.0,
                    slow_pct=100 if _mr>=54 else 0,
                    fast_pct=100 if _mr<=47 else 0,
                    label=_label, lamp=_lamp,
                    elem_adv=_elem_adv, comment=_comment)
    else:
        pace = get_pace_prediction(race_dist, target_venue, nige_count, senkou_count)

    with st.spinner('基準テーブルを構築中...'):
        base_dict, 稍重_dict, race_base_dict = build_base_table(base_file.read())
        base_file.seek(0)  # 再読み込みのためリセット

    # ---- 1200m専用AIへの自動切り替え ----
    # レース距離が1200m前後（±100m）の場合、既存の汎用calc_lpiではなく
    # 1200m専用のcalc_lpi_1200m（先行好走ボーナス・着順加点・格上挑戦ペナルティ）を使う。
    # 検証済み（2023-2025年・33レース）: 馬連3点ボックス的中率21.2%・回収率312.1%
    is_1200m_mode = abs(race_dist - 1200) <= 100

    with st.spinner('LPI計算中...'):
        if is_1200m_mode:
            _target_grade = extract_grade(race_name) or 'G3'
            results_1200 = calc_lpi_1200m(
                entry_file.read(),
                base_dict, 稍重_dict,
                target_venue=target_venue,
                target_grade=_target_grade,
            )
            entry_file.seek(0)
            # calc_lpi互換のキーを補完してランキング表で使えるようにする
            results = []
            for r in results_1200:
                results.append({
                    **r,
                    'avg_lpi': r['avg_lpi'], 'avg_venue_lpi': r['avg_venue_lpi'],
                    'g1_lpi_bonus': 0.0,
                    'g1_bonus_detail': (
                        f"1200m専用AI: 先行好走+{r['senkou_bonus']:.2f} / 着順加点+{r['rank_bonus']:.2f}"
                        + (' / ⚠️格上挑戦ペナルティ適用' if r['is_kakuwami'] else '')
                    ),
                    'n_valid': r['n_runs_used'], 'n_total': r['n_runs_used'],
                    'dom_elem': '1200m専用', 'coef': 1.0,
                    'runs': [], 'pos_pred': None, 'agari_pred': None,
                })
            st.info(
                f'🟣 1200m専用AIモードで計算しました（距離{race_dist}m）。'
                f'先行好走ボーナス・着順加点・格上挑戦ペナルティの3要素で評価しています。'
            )
        else:
            results = calc_lpi(
                entry_file.read(),
                base_dict, 稍重_dict,
                target_track=track_code,
                target_venue=target_venue,
                bonus_strength=bonus_strength,
                pace_pred_rpci=pace['pred_rpci'],
                race_base_dict=race_base_dict,
                target_race_name=race_name,
                target_front_1f_input=target_front_1f if use_pci_cs else None,
                cushion_correction_input=cushion_adj if use_cushion else 0.0,
            )

    if not results:
        st.error('計算できるデータがありませんでした。CSVの形式を確認してください。')
        st.stop()

    st.success(f'✅ {len(results)}頭 計算完了')

    # ---- ペース予測バナー ----
    lamp_color  = {'🟠': '#E65100', '🔵': '#0D47A1', '⚪': '#424242'}
    border_color = {'🟠': '#FF6D00', '🔵': '#1565C0', '⚪': '#616161'}
    bc  = lamp_color.get(pace['lamp'], '#424242')
    brd = border_color.get(pace['lamp'], '#616161')

    adv_html = ''
    if pace['elem_adv']:
        adv_html = '  有利な要素型: **' + ' / '.join(pace['elem_adv']) + '**'

    cushion_html = ''
    if use_cushion and cushion_adj != 0.0:
        c_label = '軟らかめ' if cushion_val < 8 else ('やや軟らかめ' if cushion_val < 9 else ('やや硬め' if cushion_val < 11 else '硬め'))
        cushion_html = f'　🌿 クッション値{cushion_val:.1f}({c_label}) → 基準上がり{cushion_adj:+.2f}秒補正'

    st.markdown(
        f"""<div style="background:{bc};border:2px solid {brd};border-radius:8px;
        padding:12px 16px;margin:8px 0;font-size:13px;line-height:1.8;color:#FFFFFF;font-weight:500">
        <b>{pace['lamp']} ペース予測: {pace['label']}</b>　
        予測RPCI <b>{pace['pred_rpci']:.1f}</b>（基準{pace['base_rpci']:.1f}±{pace['std']:.1f}）<br>
        スロー率 <b>{pace['slow_pct']}%</b>　ハイ率 <b>{pace['fast_pct']}%</b><br>
        {pace['comment']}{adv_html}{cushion_html}
        </div>""",
        unsafe_allow_html=True
    )

    # ---- レース環境スコア（堅実軸）バナー ----
    # レース名からグレードを推定（race_nameに"G1"等が含まれる場合のみ判定）
    _race_grade = extract_grade(race_name)
    race_env_score = calc_race_env_score(pace['pred_rpci'], race_dist, _race_grade, target_venue)
    if race_env_score <= 1:
        env_label = '🟢 堅実軸が機能しやすいレース'
        env_detail = ('少頭数寄り・Sペース寄り・マイル以上・主要場グレード戦の傾向'
                       'がそろっており、過去データではLPI上位馬の単勝回収率が高い（複勝率29.5%・回収率98.4%）。')
        env_color, env_border = '#1B5E20', '#2E7D32'
    elif race_env_score >= 3:
        env_label = '🔴 紛れが起きやすいレース（LPI上位でも過信注意）'
        env_detail = ('短距離・Hペース・G3・小場開催の条件が重なっており、'
                       '過去データではLPI上位馬でも単勝回収率が下がる傾向（複勝率は同水準・回収率66.1%）。'
                       'LPI下位の馬も含めて広めに見る方が無難。')
        env_color, env_border = '#B71C1C', '#C62828'
    else:
        env_label = '🟡 標準的な紛れやすさのレース'
        env_detail = '極端な傾向はない。通常通りLPI評価を参考にする。'
        env_color, env_border = '#5D4037', '#6D4C41'

    st.markdown(
        f"""<div style="background:{env_color};border:2px solid {env_border};border-radius:8px;
        padding:10px 16px;margin:4px 0 8px 0;font-size:12.5px;line-height:1.7;color:#FFFFFF;font-weight:500">
        <b>{env_label}</b>（環境スコア{race_env_score}/4）<br>
        {env_detail}
        </div>""",
        unsafe_allow_html=True
    )

    # ---- 1200m爆穴ゾーン バナー ----
    is_bk_zone = is_1200m_bakuketsu_zone(race_dist)
    if is_bk_zone:
        st.markdown(
            """<div style="background:#4A148C;border:2px solid #6A1B9A;border-radius:8px;
            padding:10px 16px;margin:4px 0 8px 0;font-size:12.5px;line-height:1.7;color:#FFFFFF;font-weight:500">
            <b>🟣 1200m爆穴ゾーン</b><br>
            1200m前後は前半3F・後半3Fのみで決着が単純なため、世間の評価と実力のズレが
            出やすい距離帯（過去データで10人気以下の単勝回収率132.4%、全体平均73.3%より高い）。
            ランキング表の「爆穴候補」欄でLPI上位だが目立たない馬をチェック。
            </div>""",
            unsafe_allow_html=True
        )


    # ---- タブで表示 ----
    tab1, tab2, tab3, tab4 = st.tabs(['📊 ランキング表', '📈 グラフ', '🔍 過去走詳細', '🎲 シミュレーション'])

    # ===== タブ1: ランキング表 =====
    with tab1:
        st.subheader(f'{race_name}  LPI v11 ランキング')

        # 表データ作成
        # PCI-CS計算（サイドバーでtarget設定済みの場合）
        pci_cs_map = {}
        if use_pci_cs and target_front_1f:
            for r in results:
                cs = calc_pci_cs(r.get('pci_cs_runs', []), target_front_1f)
                pci_cs_map[r['horse']] = cs

        rows = []
        for i, r in enumerate(results):
            bonus_runs = [rn for rn in r['runs'] if rn['hb'] > 0]
            bonus_str  = ' / '.join(
                [f"{rn['race']}({rn['hb_r']})" for rn in bonus_runs])
            g1_bonus_str = (f"+{r['g1_lpi_bonus']:.1f}({r['g1_bonus_detail']})"
                           if r.get('g1_lpi_bonus', 0) > 0 else '-')
            past  = [rn for rn in r['runs']
                     if not rn['excluded_baba'] and not rn['excluded_track']][:5]
            plpi  = [round(rn['lpi'], 1) for rn in past]
            while len(plpi) < 5: plpi.append('-')

            delta = r['venue_delta']
            # ペース適合判定
            pace_match = r['dom_elem'] in pace['elem_adv'] if pace['elem_adv'] else None
            pace_mark = '◎' if pace_match else ('△' if pace_match is False else '-')

            # 末脚Z（信頼性付き）
            if r.get('agari_pred'):
                ap = r['agari_pred']
                z_val   = round(ap['pred_z'], 3)
                grade   = ap['grade_label']        # 🔴A / 🟡B / ⚪C
                conf    = ap['confidence']          # ◎○△
                n_valid = ap['n_valid']
                n_disc  = ap.get('n_discounted', 0)
                # G1/G2限定フィルター適用有無
                hg_only = '★G1/G2限定' if ap.get('comment','') and 'G1/G2走' in ap.get('comment','') else ''
                matsu_str = f'{grade} {conf}  Z={z_val:+.3f}({n_valid}走{hg_only})'
            else:
                matsu_str = '-'; z_val = '-'

            # PCI追走スコア
            pci_str = (pci_cs_map[r['horse']]['judge'] + ' ' +
                       str(pci_cs_map[r['horse']]['score'])
                       + '（' + pci_cs_map[r['horse']]['detail'][:15] + '）')                        if r['horse'] in pci_cs_map else '-'

            # 予測ポジション
            if r.get('pos_pred'):
                pp = r['pos_pred']
                avg_gap = (sum(pp['past_gaps'])/len(pp['past_gaps'])
                           if pp['past_gaps'] else pp['pred_gap'])
                pos_str = (f"{pp['icon']}{pp['zone_name']} {pp['confidence']}"
                           f"  予測{pp['pred_gap']:.1f}秒（平均{avg_gap:.1f}秒）")
            else:
                pos_str = '-'

            # 過去ポジション（予測ではなく過去走の地点差実績）
            pp = r.get('pos_pred')
            if pp and pp.get('past_gaps'):
                gaps = pp['past_gaps']
                avg_gap = sum(gaps)/len(gaps)
                gap_label = ('🏇逃げ' if avg_gap<=0.1 else
                             '🔵先行' if avg_gap<=0.6 else
                             '🟡中団' if avg_gap<=1.2 else '🔴後方')
                past_pos_str = f'{gap_label} 平均{avg_gap:.1f}秒({len(gaps)}走)'
            else:
                past_pos_str = '-'

            # 堅実軸マーク: レース環境スコア<=1（紛れにくい）かつLPI上位5位以内
            # 検証済み: この条件で複勝率29.5%・単勝回収率98.4%（2024-2025年816件）
            if race_env_score <= 1 and (i + 1) <= 5:
                kentaku_str = '🟢堅実軸'
            elif race_env_score >= 3 and (i + 1) <= 5:
                kentaku_str = '🔴過信注意'
            else:
                kentaku_str = '-'

            # 爆穴候補マーク: 1200m前後のレースで、LPI4-8位（上位だが1-3位ほど目立たない）の馬
            # 検証済み: 1200m×LPI8位以内×10人気以下で47件中回収率128.7%（条件なしの67.8%より高い）
            # 出走表に人気データが無いため「LPI順位が高いのに上位3位には入らない」を
            # 「世間の評価と実力のズレ」の代理指標として使う
            if is_bk_zone and 4 <= (i + 1) <= 8:
                bakuketsu_str = '🟣爆穴候補'
            else:
                bakuketsu_str = '-'

            rows.append({
                '順位':           i + 1,
                '馬名':           r['horse'],
                f'LPI[{target_venue}補正]': r['avg_venue_lpi'],
                'LPI基本':        r['avg_lpi'],
                'G1好走B':        g1_bonus_str,
                '要素型':         r['dom_elem'],
                '係数':           r['coef'],
                '有効/全走':      f"{r['n_valid']}/{r['n_total']}",
                '1走前':          plpi[0],
                '2走前':          plpi[1],
                '3走前':          plpi[2],
                '4走前':          plpi[3],
                '5走前':          plpi[4],
                'PCI追走':        pci_str,
                '末脚能力':       matsu_str,
                '過去ポジション':  past_pos_str,
                '不利ボーナス':   bonus_str,
                '堅実軸':         kentaku_str,
                '爆穴候補':       bakuketsu_str,
            })

        result_df = pd.DataFrame(rows)
        lpi_col   = f'LPI[{target_venue}補正]'

        # カラーハイライト
        # highlight関数はhighlight_with_tに統合

        def highlight_with_t(row):
            # LPI上位3頭をハイライト
            try:
                lpi_rank = int(row.get('順位', 99) or 99)
            except (TypeError, ValueError):
                lpi_rank = 99
            if lpi_rank == 1: return ['background-color: #F9A825; color: #000; font-weight:bold'] * len(row)
            if lpi_rank == 2: return ['background-color: #1565C0; color: #fff; font-weight:bold'] * len(row)
            if lpi_rank == 3: return ['background-color: #BF360C; color: #fff; font-weight:bold'] * len(row)
            if lpi_rank <= 5: return ['background-color: #1B1B2F; color: #E0E0E0'] * len(row)
            return [''] * len(row)

        fmt = {lpi_col: '{:.1f}', 'LPI基本': '{:.1f}',
               'LPI最高': '{:.1f}', 'LPI直近': '{:.1f}', '係数': '{:.2f}'}
        # 末脚Zは数値と'-'が混在するためformat辞書には入れず事前に文字列化

        st.dataframe(
            result_df.style
                .apply(highlight_with_t, axis=1)
                .format(fmt, na_rep='-')
                .set_properties(**{'border': '1px solid #444', 'font-size': '13px'})
                .hide(axis='index'),
            use_container_width=True,
            height=min(600, 45 + len(rows) * 38),
        )

        # Excel ダウンロード
        buf = io.BytesIO()
        result_df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button(
            '📥 Excelダウンロード',
            data=buf,
            file_name=f'lpi_{race_name}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    # ===== タブ2: グラフ =====
    with tab2:
        st.subheader('LPI ランキンググラフ')
        fig = plot_ranking(results, race_name, target_venue)
        st.pyplot(fig)

        # 要素型の説明
        with st.expander('要素型の見方'):
            st.markdown("""
| 要素型 | 説明 | 東京係数 | 阪神係数 |
|--------|------|---------|---------|
| 🟢 ギアチェンジ | 後傾×差し+速上がり | **1.28** | **1.30** |
| 🔵 ロンスパ・GC | 後傾×先行+速上がり | 1.20 | 1.29 |
| 🟠 基礎スピード | 前傾×先行 | 0.77 | 1.05 |
| 🔴 パワー・ロンスパ | 前傾×差し | 1.08 | 0.89 |
| ⚫ ロンスパ | 後傾×差し+遅上がり | 0.44 | 0.39 |
""")

    # ===== タブ3: 過去走詳細 =====
    with tab3:
        st.subheader('過去走 詳細データ')
        sel = st.selectbox('馬を選択', [r['horse'] for r in results])
        hr  = next((r for r in results if r['horse'] == sel), None)

        if hr:
            col1, col2, col3, col4 = st.columns(4)
            # ポジション予測サマリー
            if hr.get('pos_pred'):
                pp = hr['pos_pred']
                st.markdown(
                    f"**予測ポジション:** {pp['icon']} {pp['label']}　"
                    f"予測地点差 **{pp['pred_gap']:.2f}秒**　"
                    f"安定度: **{pp['confidence']}**（過去{pp['n_valid']}走 std={pp['gap_std']:.3f}）",
                )
            if hr.get('agari_pred'):
                ap = hr['agari_pred']
                # ペース帯別Z表示
                pace_z_parts = []
                for p, lbl in [('H','🔵ハイ'),('M','🟢ミドル'),('S','🟠スロー')]:
                    z_val = ap['z_by_pace'].get(p)
                    n_val = ap['n_by_pace'].get(p, 0)
                    if z_val is not None:
                        pace_z_parts.append(f'{lbl}: **{z_val:+.2f}** (n={n_val})')
                    else:
                        pace_z_parts.append(f'{lbl}: データなし')
                pace_z_str = '　'.join(pace_z_parts)

                used_pace_lbl = {'H':'ハイペース','M':'ミドル','S':'スロー',None:'全体'}
                st.markdown(
                    f"**上がり予測:** {ap['grade_label']}　{ap['confidence']}　"
                    f"予測上がり **{ap['pred_agari']}秒**（コース基準{ap['course_base']:.1f}秒）{ap.get('gap_note','')}\n\n"
                    f"ペース帯別Z → {pace_z_str}\n\n"
                    f"{ap['comment']}",
                )
            col1.metric('LPI補正', f"{hr['avg_venue_lpi']:.1f}")
            col2.metric('LPI基本', f"{hr['avg_lpi']:.1f}")
            col3.metric('要素型',  hr['dom_elem'])
            col4.metric('有効走',  f"{hr['n_valid']}/{hr['n_total']}走（好走{hr['n_good']}）")

            st.markdown('---')
            run_rows = []
            for rn in hr['runs']:
                excl_reason = []
                if rn['excluded_baba']:  excl_reason.append('重/不良')
                if rn['excluded_track']: excl_reason.append('トラック違い')
                run_rows.append({
                    '走前':     rn['n'],
                    'レース名': rn['race'],
                    '競馬場':   rn['venue'],
                    '距離':     int(rn['dist']),
                    '馬場':     rn['baba'],
                    'RPCI':     rn['rpci'],
                    '地点差':   rn['gap_est'],
                    '上がり':   rn['agari'],
                    '斤量補正': rn['wt_corr'],
                    'Zスコア':  rn['z'],
                    'pb(位置補正)': rn['pb'],
                    'hb(不利B)':   rn['hb'],
                    'LPI':      rn['lpi'],
                    '要素型':   rn['elem'],
                    '前半速度Z': rn.get('front_pace_z', '-'),
                    '除外':     '⚠️ ' + '/'.join(excl_reason) if excl_reason else '✅',
                    '不利理由': rn['hb_r'],
                })

            run_df = pd.DataFrame(run_rows)

            def highlight_run(row):
                if row['除外'] != '✅':
                    return ['opacity: 0.4; color: gray'] * len(row)
                return [''] * len(row)

            st.dataframe(
                run_df.style
                    .apply(highlight_run, axis=1)
                    .format({'LPI': '{:.1f}', 'Zスコア': '{:.3f}',
                             'pb(位置補正)': '{:.3f}', 'hb(不利B)': '{:.3f}',
                             '斤量補正': '{:+.2f}'}),
                use_container_width=True,
            )

    # ===== タブ4: モンテカルロシミュレーション =====
    with tab4:
        st.subheader('🎲 モンテカルロ シミュレーション')
        st.markdown(
            '予測上がり・予測地点差の**誤差範囲でランダムにばらつかせて**1万回レースを試行し、'
            '各馬の勝利確率・複勝確率を推定します。'
        )

        # シミュレーション対象馬（pos_pred・agari_pred が揃っている馬）
        sim_horses = [(r['horse'],
                       r['pos_pred']['pred_gap'],
                       r['agari_pred']['pred_agari'])
                      for r in results
                      if r.get('pos_pred') and r.get('agari_pred')]
        # 安定度表示用
        sim_stability = {
            r['horse']: {
                'agari_conf': r['agari_pred'].get('confidence','△不安定'),
                'gap_conf':   r['pos_pred'].get('confidence','△不安定'),
                'z_std':      r['agari_pred'].get('z_std', 0.5),
                'gap_std':    r['pos_pred'].get('gap_std', 0.5),
            }
            for r in results if r.get('pos_pred') and r.get('agari_pred')
        }

        if len(sim_horses) < 2:
            st.warning('予測ポジション・上がり予測が計算できた馬が2頭未満のため実行できません。')
        else:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                n_trials = st.select_slider(
                    '試行回数',
                    options=[1000, 3000, 5000, 10000],
                    value=5000,
                    help='多いほど精度が上がるが時間がかかります'
                )
            with col_s2:
                show_top3 = st.checkbox('複勝確率（3着以内）も表示', value=True)

            if st.button('▶️ シミュレーション実行', type='primary'):
                names      = [h[0] for h in sim_horses]
                pred_gaps  = np.array([h[1] for h in sim_horses])
                pred_agari = np.array([h[2] for h in sim_horses])
                pred_total = pred_gaps + pred_agari
                n_horses   = len(names)

                # 馬個別の安定度をσに変換
                # 上がり: agari_pred['z_std'] → σ_agari
                # 地点差: pos_pred['gap_std'] → σ_gap（そのまま使用）
                AGARI_BASE_STD = 1.065  # 全体の平均誤差std（フォールバック）
                GAP_BASE_STD   = 0.589

                sigma_agari = np.array([
                    max(0.5, min(2.0,
                        r['agari_pred']['z_std'] * 1.4
                        if r.get('agari_pred') and r['agari_pred'].get('z_std')
                        else AGARI_BASE_STD))
                    for r in results if r.get('pos_pred') and r.get('agari_pred')
                ])
                sigma_gap = np.array([
                    max(0.1, min(1.2,
                        r['pos_pred']['gap_std']
                        if r.get('pos_pred') and r['pos_pred'].get('gap_std')
                        else GAP_BASE_STD))
                    for r in results if r.get('pos_pred') and r.get('agari_pred')
                ])
                # z_std（上がり不安定度）を記録
                z_stds = np.array([
                    r['agari_pred']['z_std']
                    if r.get('agari_pred') and r['agari_pred'].get('z_std')
                    else 0.5
                    for r in results if r.get('pos_pred') and r.get('agari_pred')
                ])

                wins  = np.zeros(n_horses)
                top3s = np.zeros(n_horses)

                np.random.seed(None)
                with st.spinner(f'{n_trials:,}回シミュレーション中...'):
                    for _ in range(n_trials):
                        # 地点差: 個別σで正規分布
                        sim_gaps = np.maximum(0,
                            pred_gaps + np.random.normal(0, sigma_gap))

                        # 上がり: 個別σ + 不安定馬は上方向（速い側）を抑制
                        base_noise = np.random.normal(0, sigma_agari)
                        for i in range(n_horses):
                            if z_stds[i] > 0.7 and base_noise[i] < 0:
                                # 不安定馬の「速い方向」ばらつきを半減
                                base_noise[i] *= 0.5
                        sim_agaris = pred_agari + base_noise

                        sim_totals = sim_gaps + sim_agaris
                        order      = np.argsort(sim_totals)
                        wins[order[0]]   += 1
                        top3s[order[:3]] += 1

                # 結果DataFrame
                sim_rows = []
                for i in range(n_horses):
                    wp = wins[i]  / n_trials * 100
                    pp = top3s[i] / n_trials * 100
                    lpi_rank = next((j+1 for j,r in enumerate(results) if r['horse']==names[i]), '-')
                    stab = sim_stability.get(names[i], {})
                    sim_rows.append({
                        '勝利確率順':  i+1,
                        '馬名':        names[i],
                        'LPI順位':     lpi_rank,
                        '予測通過T':   f'{pred_total[i]:.2f}秒',
                        '上がり安定':  stab.get('agari_conf','-'),
                        'gap安定':     stab.get('gap_conf','-'),
                        '勝利確率':    f'{wp:.1f}%',
                        '複勝確率':    f'{pp:.1f}%',
                        '勝利回数':    int(wins[i]),
                    })

                sim_df = pd.DataFrame(sim_rows)
                # 勝利確率順にソート
                sim_df = sim_df.sort_values('勝利回数', ascending=False).reset_index(drop=True)
                sim_df['勝利確率順'] = range(1, len(sim_df)+1)

                # ハイライト
                def sim_highlight(row):
                    rank = row['勝利確率順']
                    if rank == 1: return ['background-color:#F9A825;color:#000;font-weight:bold']*len(row)
                    if rank == 2: return ['background-color:#1565C0;color:#fff;font-weight:bold']*len(row)
                    if rank == 3: return ['background-color:#BF360C;color:#fff;font-weight:bold']*len(row)
                    return ['']*len(row)

                display_cols = ['勝利確率順','馬名','LPI順位','予測通過T',
                                '上がり安定','gap安定','勝利確率']
                if show_top3:
                    display_cols.append('複勝確率')

                st.dataframe(
                    sim_df[display_cols].style
                        .apply(sim_highlight, axis=1)
                        .hide(axis='index'),
                    use_container_width=True,
                    height=min(600, 45 + len(sim_df)*38),
                )

                # 補足
                st.caption(
                    f'試行回数: {n_trials:,}回 ／ '
                    f'上がりσ: 馬個別（z_std×1.4, 範囲0.5〜2.0秒）／ '
                    f'地点差σ: 馬個別（gap_std, 範囲0.1〜1.2秒）／ '
                    f'不安定馬（z_std>0.7）は速い方向のばらつきを半減'
                )
                st.info(
                    '💡 勝利確率はLPI順位と異なる場合があります。'
                    '予測通過Tが近い馬は誤差の影響を受けやすく、確率が均等に近くなります。'
                    'LPI上位でも通過Tが遅い馬は勝利確率が低く出ます。'
                )

# ============================================================
# フッター
# ============================================================
st.markdown('---')
st.caption('LPI v11 | 基準: 2023〜2026年全距離重賞 | 良・稍重有効 | グレード加重平均 | 斤量補正あり')
