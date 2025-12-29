import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v1.2", layout="centered")

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

# 初始化 Session State
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []
if "item_to_fill" not in st.session_state:
    st.session_state.item_to_fill = ""

# --- 2. 加入清單 Logic ---
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
        # 清空中轉站，以便下一次輸入
        st.session_state.item_to_fill = ""
        # 注意：Streamlit 不允許在 callback 直接改 name_input
    else:
        st.toast("⚠️ 請輸入名稱同價錢")

# --- 3. 介面 (UI) ---
st.title("🛒 澳洲超市極速助手 v1.2")

# 這裡我們用一個技巧：用 label 顯示當前輸入狀態
# 並將 text_input 的值綁定，讓它每一步都反應
name_val = st.text_input(
    "1. 項目名稱 (即時聯想):", 
    value=st.session_state.item_to_fill,
    key="name_input",
    placeholder="一路打字一路出建議..."
)

# --- 即時聯想區 ---
# 只要 name_input 有字，就即時顯示建議
if name_val:
    search_term = name_val.upper()
    # 在記憶庫中尋找匹配項
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    
    if matches:
        st.write("🔍 **你是否想搵：**")
        # 用 columns 橫向排列建議按鈕
        cols = st.columns(len(matches))
        for idx, m in enumerate(matches):
            if cols[idx].button(f"✨ {m.title()}", key=f"sug_{idx}", use_container_width=True):
                st.session_state.item_to_fill = m.title()
                st.rerun()
    else:
        st.caption("✨ 新項目（未有舊紀錄）")

st.divider()

# 金額格 (Enter 提交)
col_p, col_c = st.columns(2)
with col_p:
    st.number_input(
        "2. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="price_input",
        on_change=handle_submit # 這裡撳 Enter 即加
    )

with col_c:
    current_cat = memory_dict.get(name_val.upper(), "Food 🍏")
    st.metric("預計分類", current_cat)

# 加入按鈕
if st.button("➕ 加入清單 (或按 Enter)", use_container_width=True, type="primary"):
    handle_submit()
    st.rerun()

# --- 4. 清單顯示、統計與儲存 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    # 顯示清單表格（簡潔版）
    st.dataframe(df_cart, use_container_width=True, hide_index=True)
    
    if st.button("🗑️ 清空所有項目"):
        st.session_state.shopping_cart = []
        st.rerun()

    # 計算統計
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    f_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * mult
    h_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * mult

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Food 🍏", f"${f_total:.2f}")
    c2.metric("Household 🧻", f"${h_total:.2f}")
    st.success(f"### 應付總額: ${f_total + h_total:.2f}")

    # 儲存
    if st.button("💾 儲存記憶到雲端", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 成功存入 Google Sheet！", icon="🚀")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
