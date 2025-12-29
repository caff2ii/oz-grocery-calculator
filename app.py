import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Smart", layout="centered")

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

st.title("🛒 一框式智能清單")

# --- 2. 整合輸入區 ---
with st.container():
    # 呢度係關鍵：我們用一個可以用來「搜尋」的 selectbox
    # 如果你想打全新嘅嘢，我哋加一個 "New Item" 的選項或者用下面個 logic
    
    st.subheader("新增項目")
    
    # 用一個特殊的 logic: 如果 history 冇，用戶可以輸入
    # 因為 Streamlit 原生 selectbox 不支援直接 return 未見過的 string
    # 我哋加一個 "Enter New..." 選項，或者直接用 text_input 配合 autocomplete
    
    # 這是目前最順手的做法：
    item_input = st.selectbox(
        "搜尋項目 (若冇紀錄請選 'New' 並在下方輸入):",
        options=["[New Item]"] + history_list
    )
    
    final_name = ""
    if item_input == "[New Item]":
        final_name = st.text_input("輸入新項目名稱 (e.g. Probiotics):").strip()
    else:
        final_name = item_input

    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        # 根據 final_name 自動跳分類
        suggested_cat = history_dict.get(final_name, "Food 🍏")
        cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
        category = st.selectbox("分類:", cat_options, index=cat_options.index(suggested_cat))

    if st.button("➕ 加入清單", use_container_width=True):
        if final_name and price > 0:
            st.session_state.shopping_cart.append({
                "Item": final_name,
                "Price": price,
                "Category": category
            })
            st.rerun()

# --- 3. 清單與計算 (同之前一樣) ---
# ... (顯示清單與計算折扣的代碼) ...
