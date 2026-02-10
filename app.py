import streamlit as st
import pandas as pd
import random

# アプリの基本設定
st.set_page_config(page_title="ドローン免許 習熟度管理", page_icon="🚁", layout="wide")

# --- 1. データ読み込み ---
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
        st.error(f"CSV読み込みエラー: {e}")
        return pd.DataFrame()

df_all = load_data()

# --- 2. セッション状態の初期化 ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'page' not in st.session_state:
    st.session_state.page = "ホーム・出題設定"
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False

# --- 3. クイズ開始・シャッフル関数 ---
def start_quiz(q_count, mode, target_cat=None):
    if mode == "全分野からバランスよく":
        # 1. まず全問題をシャッフルしたコピーを作る
        all_pool = df_all.sample(frac=1).to_dict('records')
        cats = ["規則", "システム", "運航", "リスク"]
        selected_questions = []
        
        # 2. 各分野から均等に取れるだけ取る
        per_cat = q_count // len(cats)
        for c in cats:
            c_df = df_all[df_all['category'] == c]
            if not c_df.empty:
                # 在庫数と目標数の小さい方を取る
                take = min(per_cat, len(c_df))
                selected_questions.extend(c_df.sample(take).to_dict('records'))
        
        # 3. 足りない分（端数や在庫不足分）を、まだ選ばれていない問題から補充する
        already_selected_ids = [q['question'] for q in selected_questions] # 問題文をキーにして重複チェック
        leftovers = [q for q in all_pool if q['question'] not in already_selected_ids]
        
        needed = q_count - len(selected_questions)
        if needed > 0:
            selected_questions.extend(leftovers[:needed])
            
        # 4. 最後に全体をもう一度シャッフル（分野が固まらないように）
        random.shuffle(selected_questions)

    else:
        # 分野指定モード：その分野から指定数取る（足りなければ全件）
        target_df = df_all[df_all['category'] == target_cat]
        take_num = min(q_count, len(target_df))
        selected_questions = target_df.sample(take_num).to_dict('records')

    # --- 選択肢のシャッフル処理（以下は前回と同じ） ---
    for q in selected_questions:
        labels = ['a', 'b', 'c', 'd', 'e']
        ans_labels = str(q['answer']).split('&')
        correct_texts = [q['clean_options'][labels.index(l)] for l in ans_labels if l in labels and labels.index(l) < len(q['clean_options'])]
        shuffled_opts = q['clean_options'][:]
        random.shuffle(shuffled_opts)
        q['display_options'] = [f"{labels[i]}. {txt}" for i, txt in enumerate(shuffled_opts)]
        new_ans = [labels[i] for i, txt in enumerate(shuffled_opts) if txt in correct_texts]
        q['correct_labels'] = "&".join(sorted(new_ans))

    # セッション状態へのセット
    st.session_state.selected_questions = selected_questions
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.show_answer = False
    st.session_state.quiz_started = True
    st.session_state.is_paused = False
    st.session_state.page = "模擬テスト開始"

# --- 4. サイドバーメニュー（整理版） ---
st.sidebar.title("🚁 Menu")
# メニューからは「テスト画面」を消し、ホームと成績のみにする
menu_options = ["ホーム・出題設定", "個人成績・習熟度"]
current_menu = st.sidebar.radio("移動先", menu_options, index=0 if st.session_state.page != "個人成績・習熟度" else 1)

# サイドバーでメニューを切り替えた時の処理
if current_menu != st.session_state.page and st.session_state.page != "模擬テスト開始":
    st.session_state.page = current_menu

# --- 5. 各画面の表示 ---

# 【ホーム画面】
if st.session_state.page == "ホーム・出題設定":
    st.title("🚁 第2等無人航空機 模擬テスト")
    
    # 中断しているテストがある場合
    if st.session_state.is_paused:
        st.warning(f"現在、テストを第 {st.session_state.idx + 1} 問で中断しています。")
        col_pa1, col_pa2 = st.columns(2)
        if col_pa1.button("▶️ 続きから再開する", use_container_width=True):
            st.session_state.page = "模擬テスト開始"
            st.rerun()
        if col_pa2.button("🗑️ テストを破棄して新しく始める", use_container_width=True):
            st.session_state.is_paused = False
            st.session_state.quiz_started = False
            st.rerun()
    else:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            q_count = col1.selectbox("問題数", [30, 50])
            mode = col2.radio("出題形式", ["全分野からバランスよく", "苦手分野を指定"])
            target_cat = None
            if mode == "苦手分野を指定":
                target_cat = st.selectbox("特訓する分野を選択", ["規則", "システム", "運航", "リスク"])
            if st.button("🚀 テストを開始する", use_container_width=True):
                start_quiz(q_count, mode, target_cat)
                st.rerun()

# 【テスト画面】
elif st.session_state.page == "模擬テスト開始":
    q = st.session_state.selected_questions[st.session_state.idx]
    
    # 上部に中断ボタンを配置
    if st.button("⬅️ 一時中断してホームに戻る"):
        st.session_state.is_paused = True
        st.session_state.page = "ホーム・出題設定"
        st.rerun()
        
    st.subheader(f"問題 {st.session_state.idx + 1} / {len(st.session_state.selected_questions)}")
    st.caption(f"分野: {q['category']}")
    st.markdown(f"#### {q['question']}")
    
    ans_list = q['correct_labels'].split('&')
    user_choices = []
    for opt in q['display_options']:
        if st.checkbox(opt, key=f"idx{st.session_state.idx}_{opt}"):
            user_choices.append(opt[0])
    
    if not st.session_state.show_answer:
        if st.button("回答を確定する"):
            if len(user_choices) != len(ans_list):
                st.error(f"{len(ans_list)}個選択してください。")
            else:
                st.session_state.show_answer = True
                st.rerun()
    else:
        is_correct = set(user_choices) == set(ans_list)
        if is_correct:
            st.success(f"⭕ 正解！ (正解: {q['correct_labels']})")
            if 'last_idx' not in st.session_state or st.session_state.last_idx != st.session_state.idx:
                st.session_state.score += 1
                st.session_state.last_idx = st.session_state.idx
        else:
            st.error(f"❌ 不正解... 正解は {q['correct_labels']}")
        st.info(f"💡 **解説**\n{q['explanation']}")
        
        if st.button("次の問題へ"):
            st.session_state.history.append({"cat": q['category'], "correct": is_correct, "q": q['question']})
            if st.session_state.idx + 1 < len(st.session_state.selected_questions):
                st.session_state.idx += 1
                st.session_state.show_answer = False
            else:
                st.balloons()
                st.session_state.quiz_started = False
                st.session_state.is_paused = False
                st.session_state.page = "個人成績・習熟度"
            st.rerun()

# 【成績画面】
elif st.session_state.page == "個人成績・習熟度":
    st.title("📊 あなたの学習習熟度")
    if not st.session_state.history:
        st.warning("まだ学習データがありません。")
    else:
        h_df = pd.DataFrame(st.session_state.history)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📁 分野別正解率")
            stats = h_df.groupby('cat')['correct'].mean() * 100
            st.bar_chart(stats)
        with col2:
            st.subheader("📈 分野別解答数")
            counts = h_df.groupby('cat')['q'].count()
            st.bar_chart(counts)
        st.subheader("🚩 復習が必要な問題（直近のミス）")
        st.table(h_df[h_df['correct'] == False][['cat', 'q']].tail(10))
        if st.button("ホームに戻る"):
            st.session_state.page = "ホーム・出題設定"
            st.rerun()