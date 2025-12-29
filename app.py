import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro", layout="centered")

# 使用 Service Account 連接
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 讀取記憶
@st.cache_data(ttl=5)
def load_memory():
    try:
        df = conn.read(worksheet="Sheet1")
        if not df.empty:
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

memory_dict = load_memory()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市計數機 (Pro版)")

# 2. 輸入 Form
with st.form(key="input_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        item = st.text_input("項目名稱 (Item):")
    with col2:
        price = st.number_input("金額 ($):", min_value=0.0, format="%.2f")
    
    cat = st.selectbox("分類 (Category):", ["Food 🍏", "Household 🧻", "Other 📦"])
    submitted = st.form_submit_button("➕ 加入清單")

    if submitted and item:
        # 如果買過，自動用返舊分類
        final_cat = memory_dict.get(item.strip().upper(), cat)
        st.session_state.shopping_cart.append({"Item": item.strip(), "Price": price, "Category": final_cat})
        st.rerun()

# 3. 顯示與計算
if st.session_state.shopping_cart:
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    f_total = df_cart[df_cart['Category'].str.contains("Food")]['Price'].sum() * mult
    h_total = df_cart[df_cart['Category'].str.contains("Household")]['Price'].sum() * mult

    st.divider()
    st.metric("Food 🍏", f"${f_total:.2f}")
    st.metric("Household 🧻", f"${h_total:.2f}")
    st.info(f"### 總額: ${f_total + h_total:.2f}")

    # 4. 儲存 (宜家有權限，一定儲到)
    if st.button("💾 儲存並更新記憶庫", type="primary", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            combined_df = pd.concat([old_df, df_cart[['Item', 'Category']]]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=combined_df)
            st.success("✅ 儲存成功！記憶庫已更新。")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
