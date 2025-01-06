import streamlit as st
from firebase_admin import db, initialize_app
import firebase_admin
from datetime import datetime

# Firebaseの初期化
if 'firebase_app' not in st.session_state:
    try:
        firebase_config = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        }

        database_url = st.secrets["firebase"]["database_url"]

        cred = firebase_admin.credentials.Certificate(firebase_config)

        try:
            firebase_admin.get_app('turing_test_app')
        except ValueError:
            initialize_app(cred, {'databaseURL': database_url}, name='turing_test_app')

        st.session_state.firebase_app = True
    except Exception as e:
        st.error(f"Firebaseの初期化に失敗しました: {e}")

def show_result_page():
    st.title('チューリングテスト - 判定結果')

    # Firebase参照
    ref_results = db.reference('results', app=firebase_admin.get_app('turing_test_app'))

    # セッションステートの初期化
    if 'evaluation_submitted' not in st.session_state:
        st.session_state.evaluation_submitted = False

    # 初期化
    evaluation_result = {}  # 空の辞書として初期化

    # フォームの作成
    with st.form("evaluation_form"):
        # 判定結果の選択
        identity = st.radio(
            "判定結果を選択してください：",
            ["人間", "AI（ロボット）"]
        )

        # 確信度のスライダー
        confidence = st.slider(
            "判断の確信度（1-10）：",
            min_value=1,
            max_value=10,
            value=5
        )

        # 理由の選択肢
        reason_category = st.multiselect(
            "判断理由（該当するものを選択してください）：",
            [
                "言語スタイル（言葉の使い方や文法）",
                "社会的・感情的（反応が変、非協力的）",
                "知識と推論（知識、時事問題）",
                "状況認識（ユーモア、矛盾）"
            ]
        )

        # 自由記述のテキストエリア
        reason_text = st.text_area(
            "判断理由を詳しく説明してください（オプション）：",
            height=150
        )

        # 送信ボタン
        submitted = st.form_submit_button("結果を送信")

        if submitted:
            if not identity:
                st.error("判定結果を選択してください。")
            elif not reason:
                st.error("判断理由を入力してください。")
            else:
                st.session_state.evaluation_submitted = True

                # 正解判定
                correct_answer = (identity == st.session_state.talk_mode)
                #日付
                current_date = datetime.now().strftime("%Y-%m-%d")
                #時間（秒）
                time_taken_seconds = round(st.session_state.get("end_time", 0) - st.session_state.get("start_time", 0))
                # 判定結果データ
                evaluation_result = {
                    "identity": identity,
                    "confidence": confidence,
                    "reason_category": reason_category,  # 選択された理由
                    "reason_text": reason_text,  # 自由記述の理由
                    "turn_count": st.session_state.get("turn_count", 0),
                    "time_taken": time_taken_seconds,
                    "messages": st.session_state.get("messages", []),  # 会話の全メッセージを含む
                    "topic": st.session_state.get("current_topic", "未設定"),
                    "talk_mode": st.session_state.get("talk_mode", "AI"),  # 実際の相手
                    "correct": correct_answer,  # 正解したかどうか
                    "timestamp": current_date
                }
                # Firebaseに保存（名前で分類）
                try:
                    user_name = st.session_state.get("user_name", "匿名")
                    user_ref = ref_results.child(user_name)  # 名前のノードに保存
                    user_ref.push(evaluation_result)  # 新しい評価データを追加
                    st.success("評価が保存されました！")
                    st.session_state.page = 'explanation'
                    st.rerun()
                except Exception as e:
                    st.error(f"Firebaseへの保存中にエラーが発生しました: {e}")

    if st.button("キャンセル（説明画面に飛びます）"):
        st.session_state.page = 'explanation'
        st.rerun()

    # # 送信後の結果表示
    # if st.session_state.evaluation_submitted:
    #     st.subheader("提出された評価：")
    #     st.write(f"判定結果： {identity}")
    #     st.write(f"確信度： {confidence}/10")
    #     st.write(f"判断理由：{reason}")

    #     # 正解判定の表示
    #     correct_text = "正解です！" if evaluation_result["correct"] else "不正解です。"
    #     st.write(f"あなたの判定は: **{correct_text}**")
    #     st.write(f"実際の相手: {evaluation_result['talk_mode']}")

    #     # 会話のターン数と時間を表示
    #     turn_count = st.session_state.get("turn_count", 0)
    #     time_taken = st.session_state.get("end_time", 0) - st.session_state.get("start_time", 0)
    #     minutes, seconds = divmod(int(time_taken), 60)
    #     st.write(f"会話のターン数： {turn_count}")
    #     st.write(f"会話にかかった時間： {minutes}分 {seconds}秒")

    #     # 会話内容を表示
    #     st.subheader("会話内容：")
    #     for message in st.session_state.get("messages", []):
    #         st.write(f"[{message['role']}] {message['content']}")
