import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro v2.3", layout="centered")

# 連接 Google Sheets
# 確保 st.connection 入面個名同 secrets.toml 入面個 [connections.gsheets] 對應
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        if df is not None and not df.empty:
            return pd.Series(df.Category.values, index=df.Item.values).to_dict()
        return {}
    except Exception as e:
        return {}

history_dict = load_data()
options = ["+ 新增項目"] + sorted(list(history_dict.keys()))

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 超市助手 v2.3")

# Selectbox 是解決瀏覽器彈窗干擾的最穩方案
selected_item = st.selectbox("1. 搜尋或選擇項目:", options=options)

if selected_item == "+ 新增項目":
    final_name = st.text_input("輸入新項目名稱:", key="manual_name").strip()
    pred_cat = "Food 🍏"
else:
    final_name = selected_item
    pred_cat = history_dict.get(selected_item, "Food 🍏")

st.divider()

col_p, col_c = st.columns(2)
with col_c:
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    category = st.selectbox(
        "2. 分類:",
        options=cat_options,
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0
    )

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01)

if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": final_name.title(),
            "Price": price,
            "Category": category
        })
        st.rerun()

if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    for i, item in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{item['Item']}** ({item['Category']})")
        c2.write(f"${item['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()
    
    total = df_cart["Price"].sum()
    st.success(f"### 總額: ${total:.2f}")

    if st.button("💾 儲存記憶庫", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            updated_df = pd.concat([old_df, df_cart[["Item", "Category"]]]).drop_duplicates(subset=["Item"], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 已儲存")
            st.cache_data.clear()
        except:
            st.error("儲存失敗，請檢查權限")
