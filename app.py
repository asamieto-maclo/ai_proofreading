import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw
import json
import re

# ページ設定
st.set_page_config(page_title="AI校正＆ヒートマップ(座標特定版)", layout="wide")
st.title("📝 AI校正・薬機法チェック（該当箇所マーク機能付き）")

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
    except Exception as e:
        return None

# ■■■ 画像に赤枠を描画する関数 ■■■
def draw_rectangles(image, json_data):
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    width, height = img_copy.size
    
    for item in json_data:
        # 座標がある場合のみ描画
        if "box_2d" in item and item["box_2d"]:
            # Geminiは [ymin, xmin, ymax, xmax] の順で 0-1000 のスケールで返してくることが多い
            ymin, xmin, ymax, xmax = item["box_2d"]
            
            # 座標をピクセルに変換
            abs_ymin = (ymin / 1000) * height
            abs_xmin = (xmin / 1000) * width
            abs_ymax = (ymax / 1000) * height
            abs_xmax = (xmax / 1000) * width
            
            # 赤い太枠を描画
            draw.rectangle([abs_xmin, abs_ymin, abs_xmax, abs_ymax], outline="red", width=5)
    
    return img_copy

# メインエリア
uploaded_file = st.file_uploader("チェックしたい画像をアップロード", type=['png', 'jpg', 'jpeg', 'webp'])

if uploaded_file and api_key:
    image = Image.open(uploaded_file)
    
    if st.button("校正チェックと場所の特定を開始", type="primary"):
        target_model_name = get_best_model(api_key)
        
        if not target_model_name:
            st.error("モデルが見つかりませんでした。")
        else:
            with st.spinner(f'{target_model_name} で解析中...'):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(target_model_name)

                    # プロンプト：JSON形式で座標(box_2d)も返すように指示
                    prompt = f"""
                    あなたはプロの校正者かつ薬機法・景表法の専門家です。
                    画像内のテキストを読み取り、指摘事項がある箇所を特定してください。

                    【出力形式】
                    必ず以下のJSON形式のリストのみを出力してください。Markdownのコードブロックは不要です。
                    座標（box_2d）は、画像全体を1000x1000とした場合の [ymin, xmin, ymax, xmax] の数値リストです。
                    
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
                    
                    # AIの回答からJSON部分だけを抽出する処理
                    response_text = response.text
                    # ```json ... ``` を取り除く
                    response_text = re.sub(r"```json|```", "", response_text).strip()
                    
                    try:
                        data = json.loads(response_text)
                        
                        # 1. 描画済み画像を作成
                        annotated_image = draw_rectangles(image, data)
                        
                        # 2. 画面表示
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("🖼️ 指摘箇所")
                            st.image(annotated_image, caption='赤枠：修正が必要な箇所', use_container_width=True)
                        
                        with col2:
                            st.subheader("📝 修正リスト")
                            # JSONを表形式で表示
                            st.table(data)
                            
                    except json.JSONDecodeError:
                        st.error("AIからの応答を解析できませんでした（JSON形式エラー）。もう一度試してください。")
                        st.write("Raw Output:", response_text)

                except Exception as e:
                    st.error("エラーが発生しました。")
                    st.error(e)

elif not api_key:
    st.info("👈 左側のサイドバーにAPIキーを入力してください。")
