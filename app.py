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

# --- 2. 加入清單 Function ---
def add_to_cart():
    # 從 session_state 攞數值
    raw_name = st.session_state.get("new_item_name", "").strip()
    price = st.session_state.get("new_item_price", 0.0)
    # 呢度攞目前選中嘅分類
    selected_cat = st.session_state.get("new_item_cat", "Food 🍏")
    
    if raw_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": raw_name.title(),
            "Price": price,
            "Category": selected_cat
        })
        # 清空名同錢，等你可以入下一樣
        st.session_state.new_item_name = ""
        st.session_state.new_item_price = 0.0
    else:
        st.toast("⚠️ 請確保有名稱同價錢")

# --- 3. 介面部分 ---
st.title("🛒 澳洲超市極速助手")

item_input = st.text_input(
    "1. 項目名稱:", 
    key="new_item_name",
    placeholder="例如 milk"
)

# Auto-complete 建議按鈕
if item_input:
    search_term = item_input.upper()
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    if matches:
        cols = st.columns(len(matches) + 1)
        cols[0].caption("🔍 建議:")
        for idx, m in enumerate(matches):
            display_name = m.title()
            if cols[idx+1].button(display_name, key=f"m_{idx}"):
                st.session_state.new_item_name = display_name
                st.rerun()

col_p, col_c = st.columns(2)

with col_p:
    # 移走行制 add_to_cart，等你可以 Tab 去下一格
    st.number_input(
        "2. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="new_item_price"
    )

with col_c:
    # 預測分類
    current_upper = item_input.strip().upper()
    auto_cat = memory_dict.get(current_upper, "Food 🍏")
    cat_list = ["Food 🍏", "Household 🧻", "Other 📦"]
    
    # 將 add_to_cart 放喺呢度，當你喺呢格撳 Enter 就會加入
    st.selectbox(
        "3. 分類:", 
        cat_list, 
        index=cat_list.index(auto_cat) if auto_cat in cat_list else 0,
        key="new_item_cat",
        on_change=add_to_cart  # <--- 喺呢度撳 Enter 完先加
    )

if st.button("➕ 手動加入清單", use_container_width=True):
    add_to_cart()
    st.rerun()

# --- 4. 顯示清單、計算、儲存 (保持不變) ---
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

    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    # 用更強壯嘅計算方法
    f_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * mult
    h_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * mult

    st.divider()
    col_f, col_h = st.columns(2)
    col_f.metric("Food 🍏", f"${f_total:.2f}")
    col_h.metric("Household 🧻", f"${h_total:.2f}")
    st.info(f"### 總額: ${f_total + h_total:.2f}")

    if st.button("💾 儲存並更新記憶庫", type="primary", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_entries = df_cart[['Item', 'Category']].copy()
            new_entries['Item'] = new_entries['Item'].str.title()
            combined_df = pd.concat([old_df, new_entries]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=combined_df)
            st.success("✅ 儲存成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
