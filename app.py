import streamlit as st
import pandas as pd
import random
import time
import os
import csv

# 1. アプリの基本設定
st.set_page_config(page_title="第2等無人航空機 試験対策", page_icon="🚁", layout="wide")

# --- データ読み込み ---
@st.cache_data(show_spinner="問題を読み込んでいます...")
def load_data():
    file_path = "quiz_data.csv"
    if not os.path.exists(file_path):
        st.error(f"ファイル '{file_path}' が見つかりません。")
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig", sep=',', engine='python', on_bad_lines='warn', quoting=csv.QUOTE_MINIMAL)
        def clean_opt(opt_str):
            opts = [o.strip() for o in str(opt_str).split('|')]
            return [o[2:].strip() if "." in o[:3] else o for o in opts]
        df['clean_options'] = df['options'].apply(clean_opt)
        return df
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
        return pd.DataFrame()

df_all = load_data()

# --- 2. セッション状態の初期化 ---
if 'history' not in st.session_state: st.session_state.history = []
if 'page' not in st.session_state: st.session_state.page = "🏠 ホーム"
if 'quiz_started' not in st.session_state: st.session_state.quiz_started = False
if 'is_paused' not in st.session_state: st.session_state.is_paused = False
if 'elapsed_time' not in st.session_state: st.session_state.elapsed_time = 0

# --- 3. クイズ開始関数 ---
def start_quiz(q_count, mode, target_cat=None):
    cats = ["規則", "システム", "運航", "リスク"]
    if df_all.empty: return
    st.session_state.time_limit = 1800 if q_count == 50 else 1080

    if mode == "全分野からバランスよく":
        all_pool = df_all.sample(frac=1).to_dict('records')
        selected = []
        per_cat = q_count // len(cats)
        for c in cats:
            c_df = df_all[df_all['category'] == c]
            if not c_df.empty: selected.extend(c_df.sample(min(per_cat, len(c_df))).to_dict('records'))
        needed = q_count - len(selected)
        if needed > 0:
            already_q = [x['question'] for x in selected]
            leftovers = [x for x in all_pool if x['question'] not in already_q]
            selected.extend(leftovers[:needed])
        random.shuffle(selected)
    else:
        target_df = df_all[df_all['category'] == target_cat]
        selected = target_df.sample(min(q_count, len(target_df))).to_dict('records')

    for q in selected:
        labels = ['a', 'b', 'c', 'd', 'e']
        correct_label = str(q['answer']).strip()
        correct_text = q['clean_options'][labels.index(correct_label)]
        
        shuffled_opts = q['clean_options'][:]
        random.shuffle(shuffled_opts)
        
        q['display_options'] = [f"{labels[i]}. {t}" for i, t in enumerate(shuffled_opts)]
        q['correct_label_shuffled'] = [labels[i] for i, t in enumerate(shuffled_opts) if t == correct_text][0]

    st.session_state.selected_questions = selected
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.show_answer = False
    st.session_state.quiz_started = True
    st.session_state.is_paused = False
    st.session_state.page = "🚁 模擬テスト"
    st.session_state.elapsed_time = 0
    st.session_state.start_timestamp = time.time()
    st.session_state.current_quiz_history = []

# --- 4. サイドバーメニュー ---
st.sidebar.markdown("### 🚁 第2等無人航空機\n### 試験対策システム")
st.sidebar.divider()
options = ["🏠 ホーム", "📊 成績・習熟度", "📖 使い方・注意点"]
if st.session_state.page == "🚁 模擬テスト": options.insert(1, "🚁 模擬テスト")
current_sel = st.sidebar.radio("メニュー", options, index=options.index(st.session_state.page))

if current_sel != st.session_state.page:
    if st.session_state.page == "🚁 模擬テスト":
        st.session_state.elapsed_time += (time.time() - st.session_state.start_timestamp)
        st.session_state.is_paused = True
    st.session_state.page = current_sel
    st.rerun()

st.caption("第2等無人航空機 学科試験対策")
st.header(st.session_state.page)
st.divider()

# --- 5. メインロジック ---

if st.session_state.page == "📖 使い方・注意点":
    st.subheader("💡 択一式試験のポイント")
    st.markdown("""
    * **一つだけ選択**: 第2等試験は三肢択一式です。アプリでも最も正しいものを一つ選ぶ形式にしています。
    * **時間配分**: 50問を30分で解くには、1問36秒のペースが必要です。
    """)
    if st.button("🏠 ホームへ戻る", use_container_width=True):
        st.session_state.page = "🏠 ホーム"; st.rerun()

elif st.session_state.page == "🏠 ホーム":
    if st.session_state.is_paused:
        st.warning(f"⚠️ テストが第 {st.session_state.idx + 1} 問で中断されています。")
        c1, c2 = st.columns(2)
        if c1.button("▶️ 続きから再開する", use_container_width=True):
            st.session_state.start_timestamp = time.time(); st.session_state.page = "🚁 模擬テスト"; st.rerun()
        if c2.button("🗑️ 破棄して新しく始める", use_container_width=True):
            st.session_state.is_paused = False; st.session_state.quiz_started = False; st.rerun()
    
    if not st.session_state.is_paused:
        with st.container(border=True):
            st.subheader("📝 出題セッティング")
            col1, col2 = st.columns(2)
            q_count = col1.selectbox("問題数", [30, 50])
            mode = col2.radio("出題形式", ["全分野からバランスよく", "苦手分野を指定"])
            target_cat = st.selectbox("特訓分野", ["規則", "システム", "運航", "リスク"]) if mode == "苦手分野を指定" else None
            st.info(f"⏱️ 制限時間: {'30分' if q_count == 50 else '18分'}")
            if st.button("🚀 テストを開始する", use_container_width=True):
                start_quiz(q_count, mode, target_cat); st.rerun()

elif st.session_state.page == "🚁 模擬テスト":
    # 1. 現在の経過時間を計算
    current_elapsed = time.time() - st.session_state.start_timestamp
    total_spent = st.session_state.elapsed_time + current_elapsed
    remaining = st.session_state.time_limit - total_spent
    
    # --- レイアウト調整：最上部に中断ボタンと情報を配置 ---
    # 比率 [1, 3] で左側に小さなボタン用スペースを確保
    col_pause, col_status = st.columns([1, 3])
    
    with col_pause:
        # 小さく「⏸ 中断」ボタンを配置
        if st.button("⏸ 中断", key="pause_btn", help="現在の進捗を保存してホームに戻ります"):
            st.session_state.elapsed_time += current_elapsed
            st.session_state.is_paused = True
            st.session_state.page = "🏠 ホーム"
            st.rerun()
            
    with col_status:
        # 残り時間と問題番号を横並びに（スマホを考慮して短縮表記）
        if remaining <= 0:
            st.error("⏰ 終了")
        else:
            m, s = divmod(int(remaining), 60)
            st.markdown(f"**⏳ {m:02d}:{s:02d} | 問 {st.session_state.idx + 1}/{len(st.session_state.selected_questions)}**")

    if remaining <= 0:
        if st.button("結果を見る", use_container_width=True):
            st.session_state.final_time_spent = st.session_state.time_limit
            st.session_state.quiz_started = False
            st.session_state.page = "📊 成績・習熟度"
            st.rerun()
    else:
        # 問題エリア
        st.divider()
        q = st.session_state.selected_questions[st.session_state.idx]
        st.caption(f"【{q['category']}】")
        st.markdown(f"### {q['question']}")
        
        # 択一式
        user_choice_text = st.radio("選択してください:", q['display_options'], index=None, key=f"r_{st.session_state.idx}")
        
        if not st.session_state.show_answer:
            if st.button("回答を確定", use_container_width=True):
                if not user_choice_text:
                    st.error("答えを選んでください")
                else:
                    st.session_state.show_answer = True
                    st.rerun()
        else:
            # （以下、正誤判定と解説のコードはそのまま）
            user_label = user_choice_text[0]
            is_ok = user_label == q['correct_label_shuffled']
            if is_ok:
                st.success("⭕ 正解！")
            else:
                st.error(f"❌ 不正解... 正解: {q['correct_label_shuffled']}")
            
            st.info(f"💡 解説: {q['explanation']}")
            
            if st.button("次の問題へ", use_container_width=True):
                res = {"cat": q['category'], "correct": is_ok, "q": q['question']}
                st.session_state.history.append(res)
                st.session_state.current_quiz_history.append(res)
                if st.session_state.idx + 1 < len(st.session_state.selected_questions):
                    st.session_state.idx += 1
                    st.session_state.show_answer = False
                else:
                    st.session_state.final_time_spent = total_spent
                    st.session_state.quiz_started = False
                    st.session_state.page = "📊 成績・習熟度"
                st.rerun()

elif st.session_state.page == "📊 成績・習熟度":
    if not st.session_state.history:
        st.info("テスト履歴がありません。")
    else:
        # 1. 今回の結果サマリー
        if hasattr(st.session_state, 'current_quiz_history') and st.session_state.current_quiz_history:
            st.subheader("🎯 今回のテスト結果")
            curr_df = pd.DataFrame(st.session_state.current_quiz_history)
            total_q = len(curr_df); correct_q = curr_df['correct'].sum()
            accuracy = (correct_q / total_q) * 100
            fm, fs = divmod(int(st.session_state.final_time_spent), 60)
            
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("正答率", f"{accuracy:.1f}%")
            c_m2.metric("得点", f"{correct_q} / {total_q}")
            c_m3.metric("総解答時間", f"{fm}分{fs}秒")
            
            if accuracy >= 80: st.balloons(); st.success("合格基準達成！本番もこの調子です。")
            else: st.warning("合格基準(80%)まであと少しです。")
            st.divider()

        # 2. 分野別集計テーブル
        st.subheader("📈 分野別・累計習熟度")
        all_df = pd.DataFrame(st.session_state.history)
        cat_stats = all_df.groupby('cat').agg(問題数=('q', 'count'), 正解数=('correct', 'sum'))
        cat_stats['正答率 (%)'] = (cat_stats['正解数'] / cat_stats['問題数'] * 100).round(1)
        st.table(cat_stats)

        # 3. 分野別・間違いリスト
        st.subheader("🚩 分野別・間違えた問題リスト")
        mistakes_df = all_df[all_df['correct'] == False]
        if mistakes_df.empty:
            st.success("現在、間違えた問題はありません。完璧です！")
        else:
            for cat in ["規則", "システム", "運航", "リスク"]:
                cat_mistakes = mistakes_df[mistakes_df['cat'] == cat]
                if not cat_mistakes.empty:
                    with st.expander(f"❌ 【{cat}】で間違えた問題を表示 ({len(cat_mistakes)}件)"):
                        for m_q in cat_mistakes['q'].unique():
                            st.write(f"・{m_q}")