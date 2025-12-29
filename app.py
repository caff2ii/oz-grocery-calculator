import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro", layout="centered")

# --- 1. 連接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_memory():
    try:
        df = conn.read(worksheet="Sheet1")
        if not df.empty:
            # 統一轉大寫做比對 Key
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

memory_dict = load_memory()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市極速助手")

# --- 2. 輸入區域 (使用 Form 確保 Enter 即 Submit 且清空) ---
# clear_on_submit=True 會喺你撳 Enter 之後自動幫你清空所有格
with st.form(key="grocery_form", clear_on_submit=True):
    st.subheader("新增項目")
    item_name = st.text_input("項目名稱 (Item Name):", placeholder="e.g. milk")
    
    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        # 預設 Food，如果你買過，後台會自動幫你更正
        category = st.selectbox("分類 (Category):", ["Food 🍏", "Household 🧻", "Other 📦"])

    submit_button = st.form_submit_button("➕ 加入清單 (或直接按 Enter)", use_container_width=True)

    if submit_button:
        if item_name.strip() and price > 0:
            raw_name = item_name.strip()
            # --- 智能分類邏輯 ---
            # 如果用家冇改分類（即係選預設），我就幫佢搵舊紀錄；如果有改過，就跟用家
            final_cat = category
            if category == "Food 🍏" and raw_name.upper() in memory_dict:
                final_cat = memory_dict[raw_name.upper()]
            
            # 加入清單
            st.session_state.shopping_cart.append({
                "Item": raw_name.title(), # 自動變第一個字大寫
                "Price": price,
                "Category": final_cat
            })
            st.rerun() # 立即刷新顯示
        else:
            st.error("請輸入有名稱同埋大於 0 嘅金額！")

# --- 3. 顯示清單與統計 ---
if st.session_state.shopping_cart:
    st.divider()
    st.subheader("📋 目前清單")
    
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i
