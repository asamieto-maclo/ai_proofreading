import streamlit as st
import google.generativeai as genai
from PIL import Image

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー(Gemini版)", layout="wide")

# タイトル
st.title("📝 AI校正・薬機法チェックアプリ（Gemini版）")
st.markdown("画像をアップロードすると、**誤字脱字**および**薬機法・景表法リスク**を指摘します。")

# サイドバー：APIキー入力
with st.sidebar:
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    st.markdown("[APIキーの取得はこちら(無料)](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    additional_rules = st.text_area("追加ルール（任意）", placeholder="例：「致します」は「いたします」に統一して")

# メインエリア
uploaded_file = st.file_uploader("チェックしたい画像をアップロード", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    # 画像を表示
    image = Image.open(uploaded_file)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(image, caption='対象画像', use_container_width=True)
    
    with col2:
        if st.button("校正チェックを開始する", type="primary"):
            with st.spinner('Geminiが画像を解析中...'):
                try:
                    # Geminiの設定
                    genai.configure(api_key=api_key)
                    # モデルの選択（Flashは高速・無料枠が広い、Proは高性能）
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    # プロンプトの作成
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
                    
                    ※読み取れない場合は「判読不能」としてください。
                    ※最後に総評として、全体的なリスク度合いとアドバイスを記述してください。
                    """

                    # Geminiに画像とテキストを渡す
                    response = model.generate_content([prompt, image])
                    
                    # 結果表示
                    st.success("チェック完了！")
                    st.markdown(response.text)
                
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

elif not api_key:
    st.info("👈 左側のサイドバーにGemini APIキーを入力してください。")
