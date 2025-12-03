import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw
import json
import re
import pandas as pd

# ページ設定
st.set_page_config(page_title="【社内用】AI校正＆薬機法チェッカー", layout="wide")

# ■■■ セキュリティ設定（ここを変更してください） ■■■
# ログインに必要なパスワード
LOGIN_PASSWORD = "Ma9logi#1117"

# ■■■ パスワード認証機能 ■■■
def check_password():
    """パスワード認証を行う関数"""
    # セッションステートの初期化
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # 認証済みならTrueを返してメイン処理へ
    if st.session_state.password_correct:
        return True

    # まだ認証していない場合は入力画面を表示
    st.markdown("### 🔒 アクセス制限")
    st.markdown("このアプリを使用するにはパスワードが必要です。")
    st.text_input(
        "パスワードを入力してください", 
        type="password", 
        key="password_input", 
        on_change=verify_password
    )
    return False

def verify_password():
    """入力されたパスワードを照合"""
    if st.session_state["password_input"] == LOGIN_PASSWORD:
        st.session_state.password_correct = True
        # 安全のため入力されたパスワードをメモリから消去
        del st.session_state["password_input"]
    else:
        st.session_state.password_correct = False
        st.error("❌ パスワードが違います")

# メイン処理の前に認証チェックを実行
# 認証が通らない限り、ここから下のコードは実行されません（st.stop）
if not check_password():
    st.stop()


# ==========================================
#  ここから下がメインアプリのコードです
# ==========================================

st.title("📝 AI校正・薬機法チェックアプリ")

# ガイド（認証通過後に表示される）
with st.expander("🔰 初めての方へ：使い方の流れ", expanded=True):
    st.markdown("""
    1. **APIキー設定**: 左側のサイドバーにGeminiのAPIキーを入力します。
    2. **画像アップロード**: チェックしたい画像（広告バナーやチラシ）をアップロードします。
    3. **ルール追加（任意）**: 「『子供』は『お子様』に統一」などの独自ルールがあればサイドバーに入力します。
    4. **チェック開始**: ボタンを押すとAIが解析を開始します。
    """)

# サイドバー
with st.sidebar:
    st.header("⚙️ 設定")
    
    # APIキー入力
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    if not api_key:
        st.warning("⚠️ APIキーを入力してください")
        st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    else:
        st.success("APIキーがセットされました")

    st.markdown("---")
    
    # 追加ルール
    st.subheader("追加指示")
    additional_rules = st.text_area(
        "カスタムルール（任意）", 
        placeholder="例：\n・「致します」は「いたします」に統一\n・断定的な表現は避ける",
        height=100
    )

# モデル選択ロジック
def get_best_model(api_key):
    try:
        genai.configure(api_key=api_key)
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        best_model = None
        for m in all_models:
            if "flash" in m and "exp" not in m and "8b" not in m:
                best_model = m
                break
        if not best_model:
            for m in all_models:
                if "flash" in m:
                    best_model = m
                    break
        if not best_model and all_models:
            best_model = all_models[0]
            
        return best_model
    except Exception:
        return None

# 赤枠描画ロジック
def draw_rectangles(image, json_data):
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    width, height = img_copy.size
    
    for item in json_data:
        if "box_2d" in item and item["box_2d"]:
            ymin, xmin, ymax, xmax = item["box_2d"]
            abs_ymin = (ymin / 1000) * height
            abs_xmin = (xmin / 1000) * width
            abs_ymax = (ymax / 1000) * height
            abs_xmax = (xmax / 1000) * width
            draw.rectangle([abs_xmin, abs_ymin, abs_xmax, abs_ymax], outline="red", width=5)
    return img_copy

# メインエリア
uploaded_file = st.file_uploader("📂 チェックしたい画像をここにドロップ", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    image = Image.open(uploaded_file)
    
    if st.button("🚀 校正・薬機法チェックを開始する", type="primary", use_container_width=True):
        
        target_model_name = get_best_model(api_key)
        
        if not target_model_name:
            st.error("モデルが見つかりませんでした。通信環境を確認してください。")
        else:
            with st.spinner(f'AI({target_model_name}) が画像を解析中... ☕'):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(target_model_name)

                    prompt = f"""
                    あなたはプロの校正者かつ薬機法・景表法の専門家です。
                    画像内のテキストを読み取り、指摘事項がある箇所を特定してください。

                    【出力形式】
                    以下のJSON形式のリストのみを出力してください（Markdownコードブロック不要）。
                    座標（box_2d）は画像全体を1000x1000とした [ymin, xmin, ymax, xmax] です。
                    
                    [
                        {{
                            "text": "指摘箇所の原文",
                            "type": "薬機法 or 誤字 or 表記揺れ",
                            "reason": "NG理由",
                            "fix": "修正案",
                            "box_2d": [0, 0, 0, 0]
                        }}
                    ]

                    【チェック観点】
                    1. 誤字脱字・文法ミス・不自然な日本語
                    2. 薬機法（医薬品医療機器等法）・景品表示法に抵触する恐れのある表現
                    
                    【追加ルール】
                    {additional_rules}
                    """

                    response = model.generate_content([prompt, image])
                    
                    response_text = response.text
                    response_text = re.sub(r"```json|```", "", response_text).strip()
                    
                    try:
                        data = json.loads(response_text)
                        annotated_image = draw_rectangles(image, data)
                        
                        st.markdown("---")
                        st.success("✅ 解析が完了しました")
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("🖼️ 指摘箇所")
                            st.image(annotated_image, caption='赤枠：修正推奨箇所', use_container_width=True)
                        
                        with col2:
                            st.subheader("📝 修正リスト")
                            df = pd.DataFrame(data)
                            
                            if not df.empty:
                                df_display = df.rename(columns={
                                    "text": "原文",
                                    "type": "種別",
                                    "reason": "指摘内容",
                                    "fix": "修正案"
                                })
                                if "box_2d" in df_display.columns:
                                    df_display = df_display.drop(columns=["box_2d"])
                                
                                st.dataframe(df_display, hide_index=True)
                                
                                csv = df_display.to_csv(index=False).encode('utf-8_sig')
                                st.download_button(
                                    label="📥 結果をCSVでダウンロード",
                                    data=csv,
                                    file_name='check_result.csv',
                                    mime='text/csv',
                                    type="primary"
                                )
                            else:
                                st.info("指摘事項は見つかりませんでした。")

                    except json.JSONDecodeError:
                        st.error("AIの応答解析に失敗しました。もう一度お試しください。")

                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

elif not api_key:
    st.info("👈 左のメニューからAPIキーを設定すると開始できます")
