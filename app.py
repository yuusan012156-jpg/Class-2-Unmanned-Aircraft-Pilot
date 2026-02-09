import streamlit as st
import pandas as pd
import random

# アプリの基本設定
st.set_page_config(page_title="消化器内視鏡技師 模擬テスト", page_icon="🏥")

# --- データの読み込み ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("quiz_data.csv", encoding="utf-8-sig")
        df['options'] = df['options'].apply(lambda x: str(x).split('|'))
        return df.to_dict('records')
    except Exception as e:
        st.error(f"エラー: quiz_data.csv の読み込みに失敗しました。{e}")
        st.stop()

quiz_pool = load_data()

# --- セッション管理の初期化 ---
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False

def start_quiz():
    # 200問から50問をランダム抽出
    sample_size = min(50, len(quiz_pool))
    st.session_state.selected_questions = random.sample(quiz_pool, sample_size)
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.show_answer = False
    st.session_state.quiz_started = True
    st.session_state.quiz_finished = False

st.title("🏥 消化器内視鏡技師 模擬テスト")
st.caption("制限時間なし：じっくり解説を読んで学習しましょう")

if not st.session_state.quiz_started:
    st.write(f"現在の登録問題数: {len(quiz_pool)}問")
    st.info("「開始」を押すと50問をシャッフル出題します。")
    if st.button("模擬テストを開始する"):
        start_quiz()
        st.rerun()

elif not st.session_state.quiz_finished:
    current_questions = st.session_state.selected_questions
    current_q = current_questions[st.session_state.idx]
    
    # 進捗表示
    st.progress((st.session_state.idx) / len(current_questions))
    st.subheader(f"問題 {st.session_state.idx + 1} / {len(current_questions)}")
    st.markdown(f"#### {current_q['question']}")
    
    user_ans = st.radio("選択肢を選んでください:", current_q['options'], key=f"q_{st.session_state.idx}")
    
    if not st.session_state.show_answer:
        if st.button("回答を確定する"):
            st.session_state.show_answer = True
            st.rerun()
    else:
        # 正誤判定
        if user_ans == current_q['answer']:
            st.success("✨ 正解！")
            if 'last_idx' not in st.session_state or st.session_state.last_idx != st.session_state.idx:
                st.session_state.score += 1
                st.session_state.last_idx = st.session_state.idx
        else:
            st.error(f"❌ 不正解... 正解は 「{current_q['answer']}」")
        
        # 解説表示
        st.info(f"💡 **解説:**\n\n{current_q['explanation']}")
        
        if st.button("次の問題へ"):
            if st.session_state.idx + 1 < len(current_questions):
                st.session_state.idx += 1
                st.session_state.show_answer = False
                st.rerun()
            else:
                st.session_state.quiz_finished = True
                st.rerun()
else:
    # 結果表示
    total = len(st.session_state.selected_questions)
    percent = (st.session_state.score / total) * 100
    st.header("🏁 テスト終了")
    st.metric("正解率", f"{percent:.1f}%")
    
    if percent >= 80:
        st.balloons()
        st.success(f"🎉 合格ラインクリア！ ({st.session_state.score}/{total})")
    else:
        st.warning(f"📉 不合格判定です。解説を読み込みましょう。 ({st.session_state.score}/{total})")
    
    if st.button("もう一度挑戦（問題をシャッフル）"):
        start_quiz()
        st.rerun()