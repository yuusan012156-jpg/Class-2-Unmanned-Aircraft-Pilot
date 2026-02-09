import streamlit as st
import pandas as pd
import random
import time

# アプリの基本設定
st.set_page_config(page_title="二等無人航空機 模擬テスト", page_icon="🚁")

# --- データの読み込み ---
@st.cache_data
def load_data():
    df = pd.read_csv("quiz_data.csv", encoding="utf-8-sig")
    df['options'] = df['options'].apply(lambda x: x.split('|'))
    return df.to_dict('records')

try:
    quiz_pool = load_data()
except FileNotFoundError:
    st.error("エラー: 'quiz_data.csv' が見つかりません。")
    st.stop()

# --- セッション管理の初期化 ---
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False

def start_quiz():
    sample_size = min(50, len(quiz_pool))
    st.session_state.selected_questions = random.sample(quiz_pool, sample_size)
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.show_answer = False
    st.session_state.quiz_started = True
    st.session_state.quiz_finished = False
    # 時間計測用
    st.session_state.start_time = time.time()      # 試験全体の開始時間
    st.session_state.q_start_time = time.time()    # 各問題の開始時間
    st.session_state.time_records = []             # 各問の所要時間記録

st.title("🚁 二等無人航空機 50問模擬テスト")

# サイドバーにタイマーを表示
if st.session_state.quiz_started and not st.session_state.quiz_finished:
    elapsed_total = time.time() - st.session_state.start_time
    remaining_total = max(0, 1800 - elapsed_total)  # 30分（1800秒）
    
    mins, secs = divmod(int(remaining_total), 60)
    st.sidebar.header("⏰ 試験タイマー")
    st.sidebar.subheader(f"残り時間: {mins:02d}:{secs:02d}")
    if remaining_total == 0:
        st.sidebar.error("⚠️ 時間切れです！")
    
    # 進捗表示
    st.sidebar.write(f"進捗: {st.session_state.idx + 1} / {len(st.session_state.selected_questions)}")

if not st.session_state.quiz_started:
    st.write(f"現在の登録問題数: {len(quiz_pool)}問")
    st.info("「開始」で50問をランダムに出題します。制限時間は30分です。")
    if st.button("テストを開始する"):
        start_quiz()
        st.rerun()

elif not st.session_state.quiz_finished:
    current_q = st.session_state.selected_questions[st.session_state.idx]
    
    st.progress((st.session_state.idx) / len(st.session_state.selected_questions))
    st.subheader(f"問題 {st.session_state.idx + 1}")
    st.markdown(f"**{current_q['question']}**")
    
    user_ans = st.radio("選択肢:", current_q['options'], key=f"q_{st.session_state.idx}")
    
    if not st.session_state.show_answer:
        if st.button("回答を確定"):
            # 回答にかかった時間を計算
            duration = time.time() - st.session_state.q_start_time
            st.session_state.time_records.append(duration)
            st.session_state.show_answer = True
            st.rerun()
    else:
        # 回答後の表示
        q_duration = st.session_state.time_records[-1]
        st.write(f"⏱️ この問題の回答時間: {q_duration:.1f} 秒")

        if user_ans == current_q['answer']:
            st.success("✨ 正解！")
            if 'last_idx' not in st.session_state or st.session_state.last_idx != st.session_state.idx:
                st.session_state.score += 1
                st.session_state.last_idx = st.session_state.idx
        else:
            st.error(f"❌ 不正解... 正解は 「{current_q['answer']}」")
        
        st.info(f"💡 解説: {current_q['explanation']}")
        
        if st.button("次の問題へ"):
            if st.session_state.idx + 1 < len(st.session_state.selected_questions):
                st.session_state.idx += 1
                st.session_state.show_answer = False
                st.session_state.q_start_time = time.time() # 次の問題の開始時間をリセット
                st.rerun()
            else:
                st.session_state.quiz_finished = True
                st.session_state.end_time = time.time() # 試験終了時間
                st.rerun()
else:
    # 結果表示
    total_time = st.session_state.end_time - st.session_state.start_time
    total_mins, total_secs = divmod(int(total_time), 60)
    
    total_q = len(st.session_state.selected_questions)
    percent = (st.session_state.score / total_q) * 100
    
    st.header("🏁 テスト終了")
    
    col1, col2 = st.columns(2)
    col1.metric("正解率", f"{percent:.1f}%")
    col2.metric("総所要時間", f"{total_mins}分{total_secs}秒")
    
    # 1問あたりの平均回答時間
    avg_time = total_time / total_q
    st.write(f"1問あたりの平均回答時間: {avg_time:.1f} 秒")

    if percent >= 80:
        st.balloons()
        st.success(f"🎉 【合格】判定ラインをクリアしました！ ({st.session_state.score}/{total_q})")
    else:
        st.error(f"📉 【不合格】あと {int(total_q*0.8 - st.session_state.score)}問正解が必要です。")
    
    if st.button("もう一度（問題をシャッフルして再開）"):
        start_quiz()
        st.rerun()