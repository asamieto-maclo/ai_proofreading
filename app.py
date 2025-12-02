import streamlit as st
import google.generativeai as genai
from PIL import Image

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー(自動取得版)", layout="wide")
st.title("📝 AI校正・薬機法チェックアプリ")

# サイドバー
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    
    # 【ここが修正点】使えるモデルを自動取得してプルダウンにする
    selected_model = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # 画像認識(generateContent)が使えるモデルだけをリストアップ
            model_list = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    model_list.append(m.name)
            
            if model_list:
                # ユーザーが見つけた "gemini-2.5..." などが含まれていればそれを選択
                st.success(f"{len(model_list)} 個のモデルが見つかりました")
                selected_model = st.selectbox("使用するモデルを選択", model_list, index=0)
            else:
                st.error("利用可能なモデルが見つかりませんでした。APIキーを確認してください。")
        except Exception as e:
            st.error(f"モデル一覧の取得に失敗: {e}")
    
    st.markdown("---")
    additional_rules = st.text_area("追加ルール（任意）", placeholder="例：「致します」は「いたします」に統一して")

# メインエリア
uploaded_file = st.file_uploader("チェックしたい画像をアップロード", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key and selected_model:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(image, caption='対象画像', use_container_width=True)
    
    with col2:
        if st.button("校正チェックを開始する", type="primary"):
            with st.spinner(f'{selected_model} で解析中...'):
                try:
                    # 選択されたモデルを使用
                    model = genai.GenerativeModel(selected_model)

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

elif not api_key:
    st.info("👈 左側のサイドバーにAPIキーを入力してください。")
elif api_key and not selected_model:
    st.warning("👈 モデルの取得に失敗しました。APIキーが正しいか、通信環境を確認してください。")
