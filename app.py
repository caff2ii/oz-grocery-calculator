import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v1.1", layout="centered")

# 連接 Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_memory():
    try:
        df = conn.read(worksheet="Sheet1")
        if not df.empty:
            # 統一存儲大寫作為對比 Key
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

memory_dict = load_memory()

# 初始化 Session State (中轉站)
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []
if "item_to_fill" not in st.session_state:
    st.session_state.item_to_fill = ""

# --- 2. 邏輯函數 ---
def handle_submit():
    # 獲取當前輸入框的值
    name = st.session_state.name_input.strip()
    price = st.session_state.price_input
    
    if name and price > 0:
        # 自動識別分類
        suggested_cat = memory_dict.get(name.upper(), "Food 🍏")
        
        # 加入清單 (統一轉 Title Case)
        st.session_state.shopping_cart.append({
            "Item": name.title(),
            "Price": price,
            "Category": suggested_cat
        })
        # 清空暫存，準備下一個項目
        st.session_state.item_to_fill = ""
        # 這裡不手動清空 name_input 以防 API Exception，
        # 我們靠 item_to_fill 在 rerun 時重置它
    else:
        st.toast("⚠️ 請輸入名稱同價錢")

# --- 3. 介面 (UI) ---
st.title("🛒 澳洲超市極速助手 v1.1")

# 名稱輸入格：value 綁定 item_to_fill 變量
name_val = st.text_input(
    "1. 項目名稱:", 
    value=st.session_state.item_to_fill,
    key="name_input",
    placeholder="例如 milk"
)

# --- Auto-complete 智能按鈕 ---
if name_val:
    search_term = name_val.upper()
    # 搵出包含關鍵字嘅前 3 個舊紀錄
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    if matches:
        cols = st.columns(len(matches) + 1)
        cols[0].caption("🔍 建議:")
        for idx, m in enumerate(matches):
            if cols[idx+1].button(m.title(), key=f"btn_{idx}"):
                # 點擊後將建議名塞入中轉站
                st.session_state.item_to_fill = m.title()
                st.rerun()

# 金額格 (Enter 即 Submit)
col_p, col_c = st.columns(2)
with col_p:
    st.number_input(
        "2. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="price_input",
        on_change=handle_submit # 喺呢度撳 Enter 即加入
    )

with col_c:
    current_cat = memory_dict.get(name_val.upper(), "Food 🍏")
    st.info(f"預計分類: {current_cat}")

# 手動加入按鈕
if st.button("➕ 手動加入 (或按 Enter)", use_container_width=True):
    handle_submit()
    st.rerun()

# --- 4. 清單、統計與儲存 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    # 顯示清單
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 折扣與計算
    st.divider()
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    f_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * mult
    h_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * mult

    st.metric("Food 🍏 (折後)", f"${f_total:.2f}")
    st.metric("Household 🧻 (折後)", f"${h_total:.2f}")
    st.success(f"### 總額: ${f_total + h_total:.2f}")

    # 寫入 Google Sheets
    if st.button("💾 儲存到 Google Sheets", type="primary", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            # 確保寫入的格式統一為 Title Case
            new_data['Item'] = new_data['Item'].str.title()
            
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("✅ 儲存成功！記憶庫已更新。")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")

else:
    st.write("---")
    st.caption("清單目前係空嘅。")
