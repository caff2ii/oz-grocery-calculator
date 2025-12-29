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
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

memory_dict = load_memory()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市極速助手")

# --- 2. 聯想詞顯示 (放喺 Form 出面，純睇唔會改 Key) ---
# 呢度用一個暫存變量嚟睇吓 user 打咗咩
temp_input = st.text_input("搜尋舊項目 (聯想用):", key="search_bar", placeholder="打字睇吓買過咩...")
if temp_input:
    matches = [m for m in memory_dict.keys() if temp_input.upper() in m][:3]
    if matches:
        st.caption(f"🔍 你以前買過: {', '.join([m.title() for m in matches])}")

# --- 3. 主要輸入 Form (清空邏輯) ---
with st.form(key="grocery_form", clear_on_submit=True):
    st.markdown("### 新增項目")
    # 呢度唔用 key，避免同出面衝突，由 Form 處理清空
    name = st.text_input("項目名稱 (Item Name):")
    
    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        category = st.selectbox("分類:", ["Food 🍏", "Household 🧻", "Other 📦"])

    submit = st.form_submit_button("➕ 加入 (按 Enter)", use_container_width=True)

    if submit:
        if name.strip() and price > 0:
            raw_name = name.strip()
            # 後台自動匹配分類
            final_cat = category
            if category == "Food 🍏" and raw_name.upper() in memory_dict:
                final_cat = memory_dict[raw_name.upper()]
            
            st.session_state.shopping_cart.append({
                "Item": raw_name.title(),
                "Price": price,
                "Category": final_cat
            })
            st.rerun()

# --- 4. 顯示清單與計算 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 計算總額
    st.divider()
    discount = st.number_input("折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    f_tot = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * mult
    h_tot = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * mult

    st.metric("Food 🍏", f"${f_tot:.2f}")
    st.metric("Household 🧻", f"${h_tot:.2f}")
    st.success(f"💰 總額: ${f_tot + h_tot:.2f}")

    if st.button("💾 儲存到 Google Sheets", type="primary", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            new_data['Item'] = new_data['Item'].str.title()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("✅ 儲存成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
