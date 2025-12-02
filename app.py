import streamlit as st
import base64
from openai import OpenAI

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー", layout="wide")

# タイトルと説明
st.title("📝 AI校正・薬機法チェックアプリ")
st.markdown("""
画像をアップロードすると、**誤字脱字・不自然な表現**に加え、
**薬機法・景品表示法**の観点からリスクのある箇所を指摘します。
""")

# サイドバー：APIキー入力欄（セキュリティのため）
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    st.markdown("[APIキーの取得はこちら](https://platform.openai.com/account/api-keys)")
    
    # ユーザーが追加指示を出せるようにする
    st.markdown("---")
    st.subheader("⚙️ カスタム設定")
    additional_rules = st.text_area("追加ルール（任意）", placeholder="例：「致します」は「いたします」に統一して")

# 画像をBase64にエンコードする関数
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# メインエリア：画像アップロード
uploaded_file = st.file_uploader("チェックしたい画像をアップロードしてください", type=['png', 'jpg', 'jpeg'])

if uploaded_file and openai_api_key:
    # 画像を表示（カラムを分けて見やすく）
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(uploaded_file, caption='アップロードされた画像', use_container_width=True)
    
    with col2:
        if st.button("校正チェックを開始する", type="primary"):
            with st.spinner('AIが画像を解析し、法律と照らし合わせています...'):
                try:
                    # 画像のエンコード
                    base64_image = encode_image(uploaded_file)
                    
                    # OpenAIクライアントの初期化
                    client = OpenAI(api_key=openai_api_key)

                    # システムプロンプト（薬機法特化）
                    system_prompt = f"""
                    あなたはプロの校正者かつ薬機法・景表法の専門家です。
                    画像内のテキストを読み取り、以下の形式でマークダウンの表を出力してください。
                    
                    【チェック観点】
                    1. 誤字脱字・文法ミス・不自然な日本語
                    2. 薬機法（医薬品医療機器等法）・景品表示法に抵触する恐れのある表現（特に「効果の保証」「最大級表現」など）
                    
                    【追加ルール】
                    {additional_rules}

                    【出力フォーマット】
                    | 対象箇所（原文） | 種別（薬機法/誤字など） | NG理由・指摘内容 | 修正案 |
                    | :--- | :--- | :--- | :--- |
                    
                    ※最後に総評として、全体的なリスク度合い（低・中・高）とアドバイスを記述してください。
                    """

                    # APIリクエスト
                    response = client.chat.completions.create(
                        model="gpt-4o", # 画像認識に強いモデル
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "この画像の文章を校正してください。"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=2000
                    )

                    # 結果の表示
                    result_text = response.choices[0].message.content
                    st.success("チェック完了！")
                    st.markdown(result_text)
                
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

elif not openai_api_key:
    st.info("👈 左側のサイドバーにOpenAI APIキーを入力してください。")