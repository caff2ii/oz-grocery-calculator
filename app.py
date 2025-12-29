import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v1.3", layout="centered")

# --- 💡 核心：停用 Safari Autocomplete 的 JavaScript ---
# 呢段 code 會搵返個輸入框，強制將佢嘅 autocomplete 熄咗佢
components.html(
    """
    <script>
        window.parent.document.querySelectorAll('input').forEach(input => {
            input.setAttribute('autocomplete', 'off');
        });
    </script>
    """,
    height=0,
)

# 連接 Google Sheets
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
if "item_to_fill" not in st.session_state:
    st.session_state.item_to_fill = ""

# --- 2. 邏輯函數 ---
def handle_submit():
    name = st.session_state.name_input.strip()
    price = st.session_state.price_input
    
    if name and price > 0:
        suggested_cat = memory_dict.get(name.upper(), "Food 🍏")
        st.session_state.shopping_cart.append({
            "Item": name.title(),
            "Price": price,
            "Category": suggested_cat
        })
        st.session_state.item_to_fill = ""
    else:
        st.toast("⚠️ 請輸入名稱同價錢")

# --- 3. 介面 (UI) ---
st.title("🛒 澳洲超市助手 v1.3")

# 名稱輸入格
name_val = st.text_input(
    "1. 項目名稱 (Safari 自動填寫已停用):", 
    value=st.session_state.item_to_fill,
    key="name_input",
    placeholder="打字即出建議..."
)

# --- 即時聯想區 ---
if name_val:
    search_term = name_val.upper()
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    
    if matches:
        st.write("🔍 **建議項目：**")
        cols = st.columns(len(matches))
        for idx, m in enumerate(matches):
            if cols[idx].button(f"✨ {m.title()}", key=f"sug_{idx}", use_container_width=True):
                st.session_state.item_to_fill = m.title()
                st.rerun()

st.divider()

# 金額格 (Enter 提交)
col_p, col_c = st.columns(2)
with col_p:
    st.number_input(
        "2. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="price_input",
        on_change=handle_submit
    )

with col_c:
    current_cat = memory_dict.get(name_val.upper(), "Food 🍏")
    st.metric("預計分類", current_cat)

if st.button("➕ 加入清單 (Enter)", use_container_width=True, type="primary"):
    handle_submit()
    st.rerun()

# --- 4. 清單與統計 (簡化顯示) ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    st.table(df_cart) # 用 table 喺手機睇會更穩定
    
    if st.button("🗑️ 清空"):
        st.session_state.shopping_cart = []
        st.rerun()

    # 計算總額
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    f_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * mult
    h_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * mult

    st.divider()
    st.success(f"### 應付總額: ${f_total + h_total:.2f}")

    if st.button("💾 儲存記憶庫", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 成功存入雲端！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
