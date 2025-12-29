import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro", layout="centered")

# --- 1. 讀取數據 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        h_dict = pd.Series(df.Category.values, index=df.Item.values).to_dict()
        h_list = sorted(df.Item.unique().tolist())
        return h_dict, h_list
    except:
        return {}, []

history_dict, history_list = load_data()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市智能助手")

# --- 2. 穩定輸入區 ---
with st.container():
    st.subheader("新增項目")
    
    # 用普通 text_input，保證 Enter 鍵一定能觸發
    item_name = st.text_input("項目名稱 (例如: Milk):", key="item_name_input").strip()
    
    # 智能聯想：如果輸入咗部分文字，顯示匹配嘅舊項目
    if item_name:
        matches = [m for m in history_list if item_name.lower() in m.lower()][:5]
        if matches:
            st.write("🔍 你係咪想搵：")
            cols = st.columns(len(matches))
            for i, match in enumerate(matches):
                if cols[i].button(match, key=f"match_{i}"):
                    # 點擊聯想字，直接更新 session_state 並重整
                    st.session_state.temp_item = match
                    # 這裡可以加一個邏輯自動填入
    
    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        # 自動預測分類
        suggested_cat = history_dict.get(item_name, "Food 🍏")
        cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
        category = st.selectbox("分類:", cat_options, index=cat_options.index(suggested_cat))

    # 加入按鈕，或直接在金額框撳 Enter 亦可
    if st.button("➕ 加入清單", use_container_width=True):
        if item_name and price > 0:
            st.session_state.shopping_cart.append({
                "Item": item_name,
                "Price": price,
                "Category": category
            })
            st.rerun()
