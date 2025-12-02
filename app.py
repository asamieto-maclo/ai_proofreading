import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw
import json
import re
import pandas as pd

# ページ設定
st.set_page_config(page_title="AI校正＆薬機法チェッカー", layout="wide")

# ■■■ ヘッダー＆使い方ガイド ■■■
st.title("📝 AI校正・薬機法チェックアプリ")

# 初見ユーザー向けのガイド（デフォルトで開いておくか、閉じておくか選べます）
with st.expander("🔰 初めての方へ：使い方の流れ（クリックで開閉）", expanded=True):
    st.markdown("""
    1. **APIキー設定**: 左側のサイドバーにGeminiのAPIキーを入力します。
    2. **画像アップロード**: チェックしたい画像（広告バナーやチラシ）をアップロードします。
    3. **ルール追加（任意）**: 「『子供』は『お子様』に統一」などの独自ルールがあればサイドバーに入力します。
    4. **チェック開始**: ボタンを押すとAIが解析を開始します。
    5. **結果確認**: 画像内の**指摘箇所（赤枠）**と、**修正案のリスト**が表示されます。
    """)

# ■■■ サイドバー設定 ■■■
with st.sidebar:
    st.header("⚙️ 設定")
    
    # APIキー入力
    api_key = st.text_input("Gemini API Key", key="gemini_api_key", type="password")
    if not api_key:
        st.warning("⚠️ まずはここにAPIキーを入力してください")
        st.markdown("[APIキーの取得はこちら(無料)](https://aistudio.google.com/app/apikey)")
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

# ■■■ 関数定義 ■■■
def get_best_model(api_key):
    """最適なモデルを自動選択する関数"""
    try:
        genai.configure(api_key=api_key)
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        best_model = None
        # 戦略: Flashかつ実験版(exp)でないものを優先
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

def draw_rectangles(image, json_data):
    """画像に赤枠を描画する関数"""
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

# ■■■ メインエリア ■■■
uploaded_file = st.file_uploader("📂 チェックしたい画像をここにドロップ", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    image = Image.open(uploaded_file)
    
    # 実行ボタン（目立つように）
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
                    
                    # JSON抽出
                    response_text = response.text
                    response_text = re.sub(r"```json|```", "", response_text).strip()
                    
                    try:
                        data = json.loads(response_text)
                        
                        # 1. 画像処理
                        annotated_image = draw_rectangles(image, data)
                        
                        # 2. 結果表示エリア
                        st.markdown("---")
                        st.success("✅ 解析が完了しました")
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("🖼️ 指摘箇所")
                            st.image(annotated_image, caption='赤枠：修正推奨箇所', use_container_width=True)
                        
                        with col2:
                            st.subheader("📝 修正リスト")
                            
                            # データフレーム変換
                            df = pd.DataFrame(data)
                            
                            if not df.empty:
                                # 見やすいように列名を日本語へ整理（必要なら）
                                df_display = df.rename(columns={
                                    "text": "原文",
                                    "type": "種別",
                                    "reason": "指摘内容",
                                    "fix": "修正案"
                                })
                                # box_2dは表示しなくていいので落とす
                                if "box_2d" in df_display.columns:
                                    df_display = df_display.drop(columns=["box_2d"])
                                
                                st.dataframe(df_display, hide_index=True)
                                
                                # CSVダウンロードボタン
                                csv = df_display.to_csv(index=False).encode('utf-8_sig') # 文字化け防止のためsig付き
                                st.download_button(
                                    label="📥 結果をCSVでダウンロード",
                                    data=csv,
                                    file_name='check_result.csv',
                                    mime='text/csv',
                                    type="primary"
                                )
                            else:
                                st.info("指摘事項は見つかりませんでした。完璧です！")

                    except json.JSONDecodeError:
                        st.error("AIの応答解析に失敗しました。もう一度お試しください。")

                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

elif not api_key:
    # APIキー未入力時のプレースホルダー
    st.info("👈 左のメニューからAPIキーを設定すると開始できます")
    # デモ用のダミー画像などをここに置いても良い
