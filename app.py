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

# 初始化 Session State
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []
if "item_to_fill" not in st.session_state:
    st.session_state.item_to_fill = ""

# --- 2. 加入清單 Logic ---
def handle_submit():
    # 攞依家輸入框入面嘅嘢
    name = st.session_state.name_input.strip()
    price = st.session_state.price_input
    
    if name and price > 0:
        # 智能匹配分類
        suggested_cat = memory_dict.get(name.upper(), "Food 🍏")
        
        st.session_state.shopping_cart.append({
            "Item": name.title(),
            "Price": price,
            "Category": suggested_cat
        })
        # 清空變量
        st.session_state.item_to_fill = ""
        st.session_state.name_input = ""
        st.session_state.price_input = 0.0
    else:
        st.toast("⚠️ 請輸入名稱同價錢")

# --- 3. 介面部分 ---
st.title("🛒 澳洲超市極速助手")

# 聯想詞處理邏輯：如果點咗建議，就更新暫存
def set_item_name(name):
    st.session_state.item_to_fill = name
    # 呢度唔可以直接改 name_input，所以透過 item_to_fill 中轉

# 項目名稱輸入框
# value=st.session_state.item_to_fill 係關鍵，用嚟接收點選嘅建議
name_val = st.text_input(
    "1. 項目名稱:", 
    value=st.session_state.item_to_fill,
    key="name_input",
    placeholder="例如 milk"
)

# --- Auto-complete 聯想掣 ---
if name_val:
    search_term = name_val.upper()
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    if matches:
        cols = st.columns(len(matches) + 1)
        cols[0].caption("🔍 建議:")
        for idx, m in enumerate(matches):
            # 點一下建議，將個名填入去
            if cols[idx+1].button(m.title(), key=f"btn_{idx}"):
                st.session_state.item_to_fill = m.title()
                st.rerun()

# 金額與分類
col_p, col_c = st.columns(2)
with col_p:
    # 喺呢度撳 Enter 會觸發 on_change
    st.number_input(
        "2. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="price_input",
        on_change=handle_submit
    )

with col_c:
    # 顯示預測分類 (純顯示，費事撳 Tab 嗰陣 auto-submit 報錯)
    current_cat = memory_dict.get(name_val.upper(), "Food 🍏")
    st.write(f"預測分類: {current_cat}")

if st.button("➕ 手動加入", use_container_width=True):
    handle_submit()
    st.rerun()

# --- 4. 顯示清單與儲存 ---
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

    # 計算折扣後總額
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    f_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * mult
    h_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * mult

    st.divider()
    st.metric("Food 🍏", f"${f_total:.2f}")
    st.metric("Household 🧻", f"${h_total:.2f}")
    st.success(f"### 總額: ${f_total + h_total:.2f}")

    if st.button("💾 儲存到 Google Sheets", type="primary", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("✅ 儲存成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
