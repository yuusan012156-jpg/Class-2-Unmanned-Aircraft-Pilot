import streamlit as st
import pandas as pd
import random
import time

# 1. アプリの基本設定
st.set_page_config(page_title="第2等無人航空機 試験対策", page_icon="🚁", layout="wide")

# --- データ読み込み ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("quiz_data.csv", encoding="utf-8-sig", sep=',', engine='python')
        def clean_opt(opt_str):
            opts = [o.strip() for o in str(opt_str).split('|')]
            return [o[2:].strip() if "." in o[:3] else o for o in opts]
        df['clean_options'] = df['options'].apply(clean_opt)
        return df
    except Exception as e:
        st.error(f"CSVの読み込み失敗: {e}")
        return pd.DataFrame()

df_all = load_data()

# --- 2. セッション状態の初期化 ---
if 'history' not in st.session_state: st.session_state.history = []
if 'page' not in st.session_state: st.session_state.page = "🏠 ホーム"
if 'quiz_started' not in st.session_state: st.session_state.quiz_started = False
if 'is_paused' not in st.session_state: st.session_state.is_paused = False
if 'elapsed_time' not in st.session_state: st.session_state.elapsed_time = 0

# --- 3. クイズ開始関数（ロジック維持） ---
def start_quiz(q_count, mode, target_cat=None):
    if mode == "全分野からバランスよく":
        all_pool = df_all.sample(frac=1).to_dict('records')
        cats = ["規則", "システム", "運航", "リスク"]
        selected = []
        per_cat = q_count // 4
        for c in cats:
            c_df = df_all[df_all['category'] == c]
            if not c_df.empty:
                selected.extend(c_df.sample(min(per_cat, len(c_df))).to_dict('records'))
        already_q = [x['question'] for x in selected]
        leftovers = [x for x in all_pool if x['question'] not in already_q]
        needed = q_count - len(selected)
        if needed > 0: selected.extend(leftovers[:needed])
        random.shuffle(selected)
    else:
        target_df = df_all[df_all['category'] == target_cat]
        selected = target_df.sample(min(q_count, len(target_df))).to_dict('records')

    for q in selected:
        labels = ['a', 'b', 'c', 'd', 'e']
        ans_labels = str(q['answer']).split('&')
        correct_texts = [q['clean_options'][labels.index(l)] for l in ans_labels if l in labels]
        shuffled_opts = q['clean_options'][:]
        random.shuffle(shuffled_opts)
        q['display_options'] = [f"{labels[i]}. {t}" for i, t in enumerate(shuffled_opts)]
        new_ans = [labels[i] for i, t in enumerate(shuffled_opts) if t in correct_texts]
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
    st.session_state.time_limit = 1800 if q_count == 50 else 1080

# --- 4. サイドバーのデザイン修正 ---
st.sidebar.markdown("### 🚁 第2等無人航空機\n### 試験対策") # ここを追加
st.sidebar.divider()

options = ["🏠 ホーム", "📊 成績・習熟度"]
if st.session_state.page == "🚁 模擬テスト":
    options.insert(1, "🚁 模擬テスト")

current_sel = st.sidebar.radio("メニュー", options, index=options.index(st.session_state.page))

if current_sel != st.session_state.page:
    if st.session_state.page == "🚁 模擬テスト":
        st.session_state.elapsed_time += (time.time() - st.session_state.start_timestamp)
        st.session_state.is_paused = True
    st.session_state.page = current_sel
    st.rerun()

# --- 5. メイン画面のヘッダーデザイン修正 ---
st.caption("第2等無人航空機 試験対策") # 上に小さく表示
st.header(st.session_state.page)    # ページ名を中サイズで表示
st.divider()

# --- 【ホーム画面】 ---
if st.session_state.page == "🏠 ホーム":
    if st.session_state.is_paused:
        st.warning(f"⚠️ テストが第 {st.session_state.idx + 1} 問で中断されています。")
        c_p1, c_p2 = st.columns(2)
        if c_p1.button("▶️ 続きから再開する", use_container_width=True):
            st.session_state.start_timestamp = time.time()
            st.session_state.page = "🚁 模擬テスト"
            st.rerun()
        if c_p2.button("🗑️ 破棄して新しく始める", use_container_width=True):
            st.session_state.is_paused = False
            st.session_state.quiz_started = False
            st.rerun()
    
    if not st.session_state.is_paused:
        with st.container(border=True):
            st.subheader("📝 出題設定")
            col1, col2 = st.columns(2)
            q_count = col1.selectbox("問題数", [30, 50])
            mode = col2.radio("出題形式", ["全分野からバランスよく", "苦手分野を指定"])
            target_cat = st.selectbox("特訓分野", ["規則", "システム", "運航", "リスク"]) if mode == "苦手分野を指定" else None
            
            st.info(f"⏱️ 制限時間: {'30分' if q_count == 50 else '18分'}")
            if st.button("🚀 テストを開始する", use_container_width=True):
                start_quiz(q_count, mode, target_cat)
                st.rerun()

# --- 【テスト画面】 ---
elif st.session_state.page == "🚁 模擬テスト":
    now = time.time()
    rem = st.session_state.time_limit - (st.session_state.elapsed_time + (now - st.session_state.start_timestamp))
    
    if rem <= 0:
        st.error("⏰ 時間切れです！結果画面へ移動します。")
        if st.button("結果を見る"):
            st.session_state.quiz_started = False
            st.session_state.page = "📊 成績・習熟度"
            st.rerun()
    else:
        m, s = divmod(int(rem), 60)
        st.subheader(f"残り時間 {m:02d}:{s:02d} | 問題 {st.session_state.idx + 1} / {len(st.session_state.selected_questions)}")
        
        q = st.session_state.selected_questions[st.session_state.idx]
        st.caption(f"カテゴリ: {q['category']}")
        st.markdown(f"### {q['question']}")
        
        ans_needed = len(q['correct_labels'].split('&'))
        user_choices = []
        for opt in q['display_options']:
            if st.checkbox(opt, key=f"q{st.session_state.idx}_{opt}"):
                user_choices.append(opt[0])
        
        if not st.session_state.show_answer:
            if st.button("回答を確定", use_container_width=True):
                if len(user_choices) != ans_needed:
                    st.error(f"{ans_needed}個選んでください")
                else:
                    st.session_state.show_answer = True
                    st.rerun()
        else:
            is_ok = set(user_choices) == set(q['correct_labels'].split('&'))
            if is_ok:
                st.success(f"⭕ 正解！ (正解: {q['correct_labels']})")
                if 'last_idx' not in st.session_state or st.session_state.last_idx != st.session_state.idx:
                    st.session_state.score += 1
                    st.session_state.last_idx = st.session_state.idx
            else:
                st.error(f"❌ 不正解... 正解は {q['correct_labels']}")
            st.info(f"💡 **解説**\n{q['explanation']}")
            
            if st.button("次の問題へ", use_container_width=True):
                st.session_state.history.append({"cat": q['category'], "correct": is_ok, "q": q['question']})
                if st.session_state.idx + 1 < len(st.session_state.selected_questions):
                    st.session_state.idx += 1
                    st.session_state.show_answer = False
                else:
                    st.balloons()
                    st.session_state.quiz_started = False
                    st.session_state.page = "📊 成績・習熟度"
                st.rerun()

# --- 【成績画面】 ---
elif st.session_state.page == "📊 成績・習熟度":
    if not st.session_state.history:
        st.info("まだテストの履歴がありません。")
    else:
        h_df = pd.DataFrame(st.session_state.history)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("分野別正解率")
            st.bar_chart(h_df.groupby('cat')['correct'].mean() * 100)
        with col2:
            st.subheader("学習回数")
            st.bar_chart(h_df.groupby('cat')['q'].count())
        
        st.subheader("🚩 最近間違えた問題")
        st.table(h_df[h_df['correct'] == False][['cat', 'q']].tail(10))