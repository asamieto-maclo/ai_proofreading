import streamlit as st
import google.generativeai as genai
from PIL import Image

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー(自動修復版)", layout="wide")
st.title("📝 AI校正・薬機法チェックアプリ")

# サイドバー
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    st.markdown("---")
    additional_rules = st.text_area("追加ルール（任意）", placeholder="例：「致します」は「いたします」に統一して")

# ■■■ 自動で最適なモデルを探す関数 ■■■
def get_best_model(api_key):
    try:
        genai.configure(api_key=api_key)
        # 使えるモデルをすべて取得
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先順位ルール：
        # 1. 「flash」が含まれていて、「exp（実験版）」が含まれないもの（安定版Flash）
        # 2. 「flash」が含まれるものなら何でも
        # 3. それ以外（Proなど）
        
        best_model = None
        
        # 戦略1: 安定版Flashを探す
        for m in all_models:
            if "flash" in m and "exp" not in m and "8b" not in m:
                best_model = m
                break
        
        # 戦略2: なければとにかくFlashを探す
        if not best_model:
            for m in all_models:
                if "flash" in m:
                    best_model = m
                    break
                    
        # 戦略3: それでもなければリストの最初を使う
        if not best_model and all_models:
            best_model = all_models[0]
            
        return best_model, all_models
    except Exception as e:
        return None, str(e)

# メインエリア
uploaded_file = st.file_uploader("チェックしたい画像をアップロード", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    # 画像表示
    image = Image.open(uploaded_file)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(image, caption='対象画像', use_container_width=True)
    
    with col2:
        if st.button("校正チェックを開始する", type="primary"):
            # ここで自動選択を実行
            target_model_name, debug_info = get_best_model(api_key)
            
            if not target_model_name:
                st.error("モデルが見つかりませんでした。APIキーが正しいか確認してください。")
                st.error(f"詳細エラー: {debug_info}")
            else:
                # ユーザーにどのモデルが選ばれたか通知（安心感のため）
                st.info(f"💡 現在利用可能な最適なモデル **{target_model_name}** を使用して解析します。")
                
                with st.spinner(f'{target_model_name} で解析中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(target_model_name)

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
                        st.code(str(e)) # エラー内容をそのまま表示
                        if "429" in str(e):
                             st.warning("⚠️ 使いすぎて制限がかかったようです。数分待ってから再試行してください。")

elif not api_key:
    st.info("👈 左側のサイドバーにAPIキーを入力してください。")
