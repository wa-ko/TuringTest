import streamlit as st
import requests
import toml
import firebase_admin
from firebase_admin import credentials, db
import random
import time
from result import show_result_page

dify_api_key = st.secrets["secrets"]["DIFY_API_KEY"]
url = 'https://api.dify.ai/v1/chat-messages'


# セッションステート初期化
if 'page' not in st.session_state:
    st.session_state.page = 'explanation'
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.turn_count = 0
if "talk_mode" not in st.session_state:
    st.session_state.talk_mode = "AI"

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

        cred = credentials.Certificate(firebase_config)

        # Firebaseが初期化済みかどうかを確認
        try:
            app = firebase_admin.get_app('turing_test_app')  # アプリ名で取得
        except ValueError:
            app = firebase_admin.initialize_app(cred, {
                'databaseURL': database_url,
            }, name='turing_test_app')  # アプリ名で初期化

        st.session_state.firebase_app = True

    except Exception as e:
        st.error(f"Firebaseの初期化に失敗しました: {str(e)}")

ref_chats = db.reference('chats', app=firebase_admin.get_app('turing_test_app'))
ref_results = db.reference('results', app=firebase_admin.get_app('turing_test_app'))
config_ref = db.reference('config', app=firebase_admin.get_app('turing_test_app'))

# お題のリストを追加
TOPICS = [
    "旅行", "料理", "音楽", "スポーツ", "映画", "本", "趣味", "仕事",
    "季節", "動物", "食べ物", "夢", "思い出", "将来の目標",
    "好きな場所", "休日の過ごし方", "最近のニュース"
]

# ページの表示
if st.session_state.page == 'survey':
    with st.form("user_info_form"):
        st.subheader("以下の情報を入力してください")
        name = st.text_input("名前")
        gender = st.selectbox("性別", ["未選択", "男性", "女性"])
        age = st.slider("年齢", min_value=0, max_value=100, value=20)
        ai_usage = st.radio("AIの利用頻度", ["全く使わない", "月に数回", "ほとんど毎日"])

        submitted = st.form_submit_button("情報を保存してチューリングテストを開始")

        if submitted:
            if not name or gender == "未選択":
                st.error("名前と性別を入力してください。")
            else:
                # Firebaseにユーザー情報を保存
                user_data = {
                    "name": name,
                    "gender": gender,
                    "age": age,
                    "ai_usage": ai_usage,
                    "created_at": time.time()
                }
                try:
                    user_ref = ref_results.child(name)
                    user_ref.child("user_info").update(user_data)  # ユーザー情報を上書き
                    st.success("情報が保存されました！")
                    st.session_state.user_name = name  # セッションに保存
                    st.session_state.page = "chat"  # チャットページに移動
                    st.rerun()
                except Exception as e:
                    st.error(f"Firebaseへの保存中にエラーが発生しました: {e}")
            st.session_state.start_time = time.time()
    if st.button("説明ページへ戻る"):
        st.session_state.page = 'explanation'
        st.rerun()

elif st.session_state.page == 'explanation':
    try:
        ref_chats.delete()
        st.session_state.messages = []  # チャットメッセージの初期化
        st.session_state.current_topic = random.choice(TOPICS)
    except Exception as e:
        st.error(f"chatsノードの削除中にエラーが発生しました: {e}")

    st.title('チューリングテスト - 説明')
    st.markdown("""
## 概要
- このアプリは、チューリングテストを行うためのものです。
- チューリングテストは、会話の相手がコンピュータか人間かを判別できるかどうかを判断するテストです。このアプリでチャットを行いその結果を記録します。
- 会話はターン制で、連続してメッセージを送ることはせずに、交互にメッセージを送信してください。
- 会話は5分間続き、その後に結果を入力するページに移動します。
- 話題は相手には知らされていませんので注意してください。話題以外のことを話しても構いません。
- 途中で判断できて会話を終了したい場合は、会話終了ボタンをクリックしてアンケートに進んでください。
- タイマーはメッセージを送信した際に更新されます。
- なにか異常があれば、お知らせください。
- こちらの結果は研究に使用されます。※個人情報は記載されません。

チャットページに移動して、会話を始めてください。あなたから会話を始めてください。
""")

    if st.button("アンケートページへ"):
        st.session_state.page = 'survey'
        st.rerun()
    if st.button("チャットページへ"):
        st.session_state.page = 'chat'
        st.session_state.start_time = time.time()
        st.rerun()

elif st.session_state.page == 'chat':
    try:
        talk_mode_data = config_ref.get()
        if talk_mode_data:
            st.session_state.talk_mode = talk_mode_data.get('talk_mode', 'AI')
        # st.write(f"現在の会話モード: {st.session_state.talk_mode}")

    except Exception as e:
        st.error(f"Firebaseから`talk_mode`を取得できません: {e}")
    st.title('チューリングテスト')

    st.subheader(f"お題：{st.session_state.current_topic}")

    # Add a button to end the conversation
    if st.button("会話終了"):
        st.session_state.page = 'result'
        st.session_state.end_time = time.time()  # Record the end time
        st.rerun()

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = ""

    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()  # Initialize start time

    # Layout for timer and chat messages
    timer_placeholder = st.empty()
    chat_placeholder = st.container()


    # Countdown timer calculation and display
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, 300 - int(elapsed_time))  # 5 minutes = 300 seconds
    minutes, seconds = divmod(remaining_time, 60)
    timer_placeholder.subheader(f"残り時間: {minutes:02}:{seconds:02}")

    # Display chat messages
    with chat_placeholder:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    prompt = st.chat_input("ここに入力してください")

    # Check if the prompt exceeds 60 characters
    if prompt and len(prompt) > 60:
        st.error("入力は60文字以内にしてください。")
    elif prompt and remaining_time > 0:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.turn_count += 1

        if st.session_state.talk_mode == "AI":
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                headers = {
                    'Authorization': f'Bearer {dify_api_key}',
                    'Content-Type': 'application/json'
                }
                payload = {
                    "inputs": {},
                    "query": prompt,
                    "response_mode": "blocking",
                    "conversation_id": st.session_state.conversation_id,
                    "user": "alex-123",
                    "files": []
                }

            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                full_response = response_data.get("answer", "")
                new_conversation_id = response_data.get("conversation_id", st.session_state.conversation_id)
                st.session_state.conversation_id = new_conversation_id

                # Calculate delay
                char_count = len(full_response)
                delay = 0.6 * char_count + random.gammavariate(1.5, 3.5)
                time.sleep(delay)

            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred: {e}")
                full_response = "An error occurred while fetching the response."

            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        else:
            # Firebaseにメッセージを保存
            ref = db.reference('chats', app=firebase_admin.get_app('turing_test_app'))
            payload = {
                'role': 'user',
                'content': prompt,
                'timestamp': time.time(),
                'topic': st.session_state.current_topic,
                'status': 'pending'
            }

            with st.chat_message("assistant"):
                message_placeholder = st.empty()

                try:
                    # メッセージをFirebaseに保存
                    new_message_ref = ref.push(payload)

                    # 応答が返ってくるまでループ
                    while True:
                        message_data = ref.child(new_message_ref.key).get()
                        if message_data and message_data.get('status') == 'responded':
                            operator_response = message_data.get('response')
                            break

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    operator_response = "An error occurred while fetching the response."

            # 応答を表示
            message_placeholder.markdown(operator_response or "No response available.")
            st.session_state.messages.append({"role": "assistant", "content": operator_response or "No response available."})

    if remaining_time == 0:
        st.warning("会話が終了しました。")
        st.session_state.end_time = time.time()
        st.session_state.page = 'result'
        st.rerun()

elif st.session_state.page == 'result':
    show_result_page()