import streamlit as st
import google.generativeai as genai
from PIL import Image

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー(Gemini版)", layout="wide")

st.title("📝 AI校正・薬機法チェックアプリ（Gemini 1.5 Pro）")

# サイドバー
with st.sidebar:
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    st.markdown("---")
    additional_rules = st.text_area("追加ルール（任意）", placeholder="例：「致します」は「いたします」に統一して")
    
    # デバッグ用：モデル確認ボタン
    if api_key and st.button("使えるモデル一覧を表示"):
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write("利用可能なモデル:", models)
        except Exception as e:
            st.error(f"キーエラー: {e}")

# メインエリア
uploaded_file = st.file_uploader("チェックしたい画像をアップロード", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(image, caption='対象画像', use_container_width=True)
    
    with col2:
        if st.button("校正チェックを開始する", type="primary"):
            with st.spinner('Gemini 1.5 Pro が解析中...'):
                try:
                    genai.configure(api_key=api_key)
                    
                    # 【変更点】モデル名をより確実なものに変更
                    # もし gemini-1.5-pro がダメなら gemini-1.5-flash-latest などを試せます
                    model = genai.GenerativeModel('gemini-1.5-pro')

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
                    st.info("ヒント: サイドバーの「使えるモデル一覧を表示」ボタンを押して、表示されたモデル名（例: models/gemini-pro）をコード内の model = ... の部分に書き写すと解決する場合があります。")

elif not api_key:
    st.info("👈 左側のサイドバーにGemini APIキーを入力してください。")
