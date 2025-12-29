import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v1.7", layout="centered")

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
if "random_id" not in st.session_state:
    st.session_state.random_id = str(random.randint(1000, 9999))

# --- 2. 邏輯函數 ---
def add_to_cart():
    # 這裡從 session_state 獲取當前 widget 的值
    name = st.session_state.name_input.strip()
    price = st.session_state.price_input
    cat = st.session_state.cat_input
    
    if name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": name.title(),
            "Price": price,
            "Category": cat
        })
        # 重置：清空暫存並更換 ID
        st.session_state.item_to_fill = ""
        st.session_state.random_id = str(random.randint(1000, 9999))
        st.rerun()

# --- 3. 介面 (UI) ---
st.title("🛒 澳洲超市助手 v1.7")

# --- 關鍵：名稱輸入格 ---
# 我們將 value 綁定到 session_state.item_to_fill
name_val = st.text_input(
    "1. 項目名稱:", 
    value=st.session_state.item_to_fill,
    key="name_input",
    placeholder="打字後按 Tab 顯示建議",
    autocomplete="new-password"
)

# --- 智能建議區 (修正點擊填入邏輯) ---
if name_val:
    search_term = name_val.upper()
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    
    if matches:
        st.write("✨ **智能建議 (點選直接填入):**")
        cols = st.columns(len(matches))
        for idx, m in enumerate(matches):
            # 點擊建議按鈕
            if cols[idx].button(f"🛒 {m.title()}", key=f"sug_{idx}_{st.session_state.random_id}", use_container_width=True):
                # 1. 更新暫存字串
                st.session_state.item_to_fill = m.title()
                # 2. 強制刷新頁面，讓 text_input 的 value 讀取新的 item_to_fill
                st.rerun()

st.divider()

# 分類與金額
col_p, col_c = st.columns(2)

with col_c:
    # 根據當前輸入的名稱（可能是點選後的）來預測分類
    current_name = name_val.strip().upper()
    predicted_cat = memory_dict.get(current_name, "Food 🍏")
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    
    # 修正：如果預測分類在選項中，自動設定 index
    default_index = cat_options.index(predicted_cat) if predicted_cat in cat_options else 0
    
    st.selectbox(
        "2. 分類:", 
        options=cat_options,
        index=default_index,
        key="cat_input"
    )

with col_p:
    st.number_input(
        "3. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="price_input",
        step=0.01
    )

if st.button("➕ 加入清單 (Enter)", use_container_width=True, type="primary"):
    add_to_cart()

# --- 4. 清單與計算 ---
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

    # 計算統計
    st.divider()
    discount = st.number_input("折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    total = sum(item['Price'] for item in st.session_state.shopping_cart) * mult
    st.success(f"### 總額: ${total:.2f}")

    if st.button("💾 儲存並更新記憶", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 成功存入雲端！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
