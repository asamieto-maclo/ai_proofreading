import streamlit as st
import google.generativeai as genai
from PIL import Image

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー(Flash版)", layout="wide")
st.title("📝 AI校正・薬機法チェックアプリ")

# サイドバー
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    additional_rules = st.text_area("追加ルール（任意）", placeholder="例：「致します」は「いたします」に統一して")

# メインエリア
uploaded_file = st.file_uploader("チェックしたい画像をアップロード", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(image, caption='対象画像', use_container_width=True)
    
    with col2:
        if st.button("校正チェックを開始する", type="primary"):
            # ここで安定版の「gemini-1.5-flash」を固定指定
            target_model = "gemini-1.5-flash"
            
            with st.spinner(f'{target_model} で解析中...'):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(target_model)

                    prompt = f"""
                    あなたはプロの校正者かつ薬機法・景表法の専門家です。
                    画像内のテキストを読み取り、以下の形式でマークダウンの表を出力してください。
                    
                    【チェック観点】
                    1. 誤字脱字・文法ミス・不自然な日本語
                    2. 薬機法（医薬品医療機器等法）・景品表示法に抵触する恐れのある表現
                    
                    【追加ルール】
                    {additional_rules}

                    【出力フォーマット】
                    | 対象箇所（原文） | 種別（薬機法/誤字など） | NG理由・指摘内容 | 修正案 |
                    | :--- | :--- | :--- | :--- |
                    """

                    response = model.generate_content([prompt, image])
                    st.success("チェック完了！")
                    st.markdown(response.text)
                
                except Exception as e:
                    st.error("エラーが発生しました。")
                    st.error(e)
                    st.warning("もし '404 not found' が出る場合は、requirements.txt の google-generativeai>=0.8.0 を確認し、Rebootしてください。")

elif not api_key:
    st.info("👈 左側のサイドバーにAPIキーを入力してください。")
