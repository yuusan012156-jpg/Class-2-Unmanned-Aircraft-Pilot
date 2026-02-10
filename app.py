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
        df = pd.read_csv(
            file_path, 
            encoding="utf-8-sig", 
            sep=',', 
            engine='python',
            on_bad_lines='warn',
            quoting=csv.QUOTE_MINIMAL
        )
        
        required = ['question', 'category', 'options', 'answer', 'explanation']
        if not all(col in df.columns for col in required):
            st.error(f"CSVの列名が正しくありません。期待される列: {required}")
            return pd.DataFrame()

        def clean_opt(opt_str):
            opts = [o.strip() for o in str(opt_str).split('|')]
            return [o[2:].strip() if "." in o[:3] else o for o in opts]
        
        df['clean_options'] = df['options'].apply(clean_opt)
        return df
    except Exception as e:
        st.error(f"読み込みエラーが発生しました: {e}")
        return pd.DataFrame()

df_all = load_data()

# --- 2. セッション状態の初期化 ---
if 'history' not in st.session_state: st.session_state.history = []
if 'page' not in st.session_state: st.session_state.page = "🏠 ホーム"
if 'quiz_started' not in st.session_state: st.session_state.quiz_started = False
if 'is_paused' not in st.session_state: st.session_state.is_paused = False
if 'elapsed_time' not in st.session_state: st.session_state.elapsed_time = 0
if 'time_limit' not in st.session_state: st.session_state.time_limit = 1800

# --- 3. クイズ開始関数（制限時間あり） ---
def start_quiz(q_count, mode, target_cat=None):
    cats = ["規則", "システム", "運航", "リスク"]
    if df_all.empty: return
    
    # 制限時間の設定（50問なら30分、30問なら18分）
    st.session_state.time_limit = 1800 if q_count == 50 else 1080

    if mode == "全分野からバランスよく":
        all_pool = df_all.sample(frac=1).to_dict('records')
        selected = []
        per_cat = q_count // len(cats)
        for c in cats:
            c_df = df_all[df_all['category'] == c]
            if not c_df.empty:
                selected.extend(c_df.sample(min(per_cat, len(c_df))).to_dict('records'))
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
        ans_labels = str(q['answer']).split('&')
        correct_texts = [q['clean_options'][labels.index(l)] for l in ans_labels if l in labels and labels.index(l) < len(q['clean_options'])]
        shuffled_opts = q['clean_options'][:]
        random.shuffle(shuffled_opts)
        q['display_options'] = [f"{labels[i]}. {t}" for i, t in enumerate(shuffled_opts)]
        new_ans = [labels[i] for i, txt in enumerate(shuffled_opts) if txt in correct_texts]
        q['correct_labels'] = "&".join(sorted(new_ans))

    st.session_state.selected_questions = selected
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.show_answer = False
    st.session_state.quiz_started = True
    st.session_state.is_paused = False
    st.session_state.page = "🚁 模擬テスト"
    st.session_state.elapsed_time = 0
    st.session_state.start_timestamp = time.time()

# --- 4. サイドバーメニュー ---
st.sidebar.markdown("### 🚁 第2等無人航空機\n### 試験対策システム")
st.sidebar.divider()
options = ["🏠 ホーム", "📊 成績・習熟度", "📖 使い方・注意点"]
if st.session_state.page == "🚁 模擬テスト": 
    options.insert(1, "🚁 模擬テスト")

current_sel = st.sidebar.radio("メニュー", options, index=options.index(st.session_state.page))

if current_sel != st.session_state.page:
    if st.session_state.page == "🚁 模擬テスト":
        # 中断時に経過時間を蓄積
        st.session_state.elapsed_time += (time.time() - st.session_state.start_timestamp)
        st.session_state.is_paused = True
    st.session_state.page = current_sel
    st.rerun()

st.caption("第2等無人航空機 学科試験対策")
st.header(st.session_state.page)
st.divider()

# --- 5. 各メイン画面 ---

# 【使い方・注意点】
if st.session_state.page == "📖 使い方・注意点":
    st.subheader("💡 第2等無人航空機 学科試験の概要")
    st.markdown("""
    本試験は**三肢択一式**（当アプリは五肢まで対応）で行われ、高い正確性とスピードが求められます。
    * **50問 / 30分**（1問あたり36秒）
    * **合格基準**: 80%以上の正答（40問正解）
    """)
    
    with st.expander("📝 当アプリの機能紹介", expanded=True):
        st.markdown("""
        * **本番同様のカウントダウン**: 制限時間がゼロになると強制的にテストが終了します。
        * **中断・再開**: テスト中に中断しても、残りの時間は正確に保存されます。
        * **完全シャッフル**: 問題の選択肢の並び順が毎回変わるため、位置で覚えてしまうのを防ぎます。
        """)

    with st.expander("⚠️ データ作成時の注意"):
        st.markdown("""
        * 文中の半角カンマ（`,`）は使用せず、必ず**全角「、」**を使ってください。
        * 解答欄は `a` や `a&b` のように記号で入力してください。
        """)
    
    if st.button("🏠 ホームへ戻る", use_container_width=True):
        st.session_state.page = "🏠 ホーム"; st.rerun()

# 【ホーム画面】
elif st.session_state.page == "🏠 ホーム":
    if st.session_state.is_paused:
        st.warning(f"⚠️ テストが第 {st.session_state.idx + 1} 問で中断されています。")
        c1, c2 = st.columns(2)
        if c1.button("▶️ 続きから再開する", use_container_width=True):
            st.session_state.start_timestamp = time.time()
            st.session_state.page = "🚁 模擬テスト"; st.rerun()
        if c2.button("🗑️ 破棄して新しく始める", use_container_width=True):
            st.session_state.is_paused = False; st.session_state.quiz_started = False; st.rerun()
    
    if not st.session_state.is_paused:
        with st.container(border=True):
            st.subheader("📝 出題セッティング")
            col1, col2 = st.columns(2)
            q_count = col1.selectbox("問題数", [30, 50])
            mode = col2.radio("出題形式", ["全分野からバランスよく", "苦手分野を指定"])
            target_cat = st.selectbox("特訓分野", ["規則", "システム", "運航", "リスク"]) if mode == "苦手分野を指定" else None
            
            time_info = "30分" if q_count == 50 else "18分"
            st.info(f"⏱️ **制限時間: {time_info}** (本番形式のカウントダウン)")
            if st.button("🚀 テストを開始する", use_container_width=True):
                start_quiz(q_count, mode, target_cat); st.rerun()

# 【テスト画面】
elif st.session_state.page == "🚁 模擬テスト":
    # 残り時間の計算
    current_elapsed = time.time() - st.session_state.start_timestamp
    remaining = st.session_state.time_limit - (st.session_state.elapsed_time + current_elapsed)
    
    if remaining <= 0:
        st.error("⏰ 制限時間終了です！結果画面へ移動します。")
        if st.button("結果を見る"):
            st.session_state.quiz_started = False
            st.session_state.page = "📊 成績・習熟度"; st.rerun()
    else:
        m, s = divmod(int(remaining), 60)
        st.subheader(f"⏳ 残り時間 {m:02d}:{s:02d} | 問題 {st.session_state.idx + 1} / {len(st.session_state.selected_questions)}")
        
        if st.button("⬅️ 一時中断してホームに戻る"):
            st.session_state.elapsed_time += current_elapsed
            st.session_state.is_paused = True
            st.session_state.page = "🏠 ホーム"; st.rerun()

        q = st.session_state.selected_questions[st.session_state.idx]
        st.caption(f"カテゴリ: 【{q['category']}】")
        st.markdown(f"### {q['question']}")
        
        ans_labels = q['correct_labels'].split('&')
        st.info(f"💡 正解を **{len(ans_labels)}つ** 選んでください")
        
        user_choices = [opt[0] for opt in q['display_options'] if st.checkbox(opt, key=f"dr_{st.session_state.idx}_{opt}")]
        
        if not st.session_state.show_answer:
            if st.button("回答を確定", use_container_width=True):
                if len(user_choices) != len(ans_labels): st.error(f"{len(ans_labels)}個選んでください")
                else: st.session_state.show_answer = True; st.rerun()
        else:
            is_ok = set(user_choices) == set(ans_labels)
            if is_ok: st.success(f"⭕ 正解！ (正解: {q['correct_labels']})")
            else: st.error(f"❌ 不正解... 正解は {q['correct_labels']}")
            st.markdown(f"**【解説】**\n{q['explanation']}")
            if st.button("次の問題へ", use_container_width=True):
                st.session_state.history.append({"cat": q['category'], "correct": is_ok, "q": q['question']})
                if st.session_state.idx + 1 < len(st.session_state.selected_questions):
                    st.session_state.idx += 1; st.session_state.show_answer = False
                else:
                    st.balloons(); st.session_state.quiz_started = False; st.session_state.page = "📊 成績・習熟度"
                st.rerun()

# 【成績画面】
elif st.session_state.page == "📊 成績・習熟度":
    if not st.session_state.history: st.info("データがありません。")
    else:
        h_df = pd.DataFrame(st.session_state.history)
        c1, c2 = st.columns(2)
        with c1: st.subheader("分野別正解率 (%)"); st.bar_chart(h_df.groupby('cat')['correct'].mean() * 100)
        with c2: st.subheader("学習回数"); st.bar_chart(h_df.groupby('cat')['q'].count())
        st.subheader("🚩 最近間違えた問題")
        st.table(h_df[h_df['correct'] == False][['cat', 'q']].tail(10))