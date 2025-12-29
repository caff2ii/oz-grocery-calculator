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
            # 全部轉大寫做 Key，方便對比
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

memory_dict = load_memory()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

# --- 2. 加入清單 Function (處理自動大寫) ---
def add_to_cart():
    raw_name = st.session_state.new_item_name.strip()
    # 關鍵：自動將第一個字轉大寫，例如 milk -> Milk
    item_name_fixed = raw_name.title() 
    price = st.session_state.new_item_price
    
    # 智能分類：用大寫去搵舊紀錄
    suggested = memory_dict.get(raw_name.upper(), st.session_state.new_item_cat)
    
    if raw_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": item_name_fixed,
            "Price": price,
            "Category": suggested
        })
        # 清空輸入
        st.session_state.new_item_name = ""
        st.session_state.new_item_price = 0.0
    else:
        st.toast("⚠️ 請輸入名稱同價錢")

# --- 3. 介面部分 ---
st.title("🛒 澳洲超市極速助手")

# 名稱輸入
item_input = st.text_input(
    "1. 項目名稱 (例如 milk):", 
    key="new_item_name",
    placeholder="打細楷都會自動變大寫"
)

# --- Auto-complete (不分大細楷搜尋) ---
if item_input:
    search_term = item_input.upper()
    # 搵出所有包含呢個字嘅舊項目
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    
    if matches:
        cols = st.columns(len(matches) + 1)
        cols[0].caption("🔍 建議:")
        for idx, m in enumerate(matches):
            # 顯示時用 Title Case (Milk)
            display_name = m.title()
            if cols[idx+1].button(display_name, key=f"m_{idx}"):
                st.session_state.new_item_name = display_name
                st.rerun()

# 金額與分類
col_p, col_c = st.columns(2)
with col_p:
    st.number_input(
        "2. 金額 ($):", 
        min_value=0.0, 
        format="%.2f", 
        key="new_item_price",
        on_change=add_to_cart # Enter 鍵直接 Add
    )

with col_c:
    # 預測分類顯示
    current_upper = item_input.strip().upper()
    auto_cat = memory_dict.get(current_upper, "Food 🍏")
    cat_list = ["Food 🍏", "Household 🧻", "Other 📦"]
    
    st.selectbox(
        "3. 分類:", 
        cat_list, 
        index=cat_list.index(auto_cat) if auto_cat in cat_list else 0,
        key="new_item_cat"
    )

if st.button("➕ 加入清單", use_container_width=True):
    add_to_cart()
    st.rerun()

# --- 4. 顯示清單與儲存 ---
if st.session_state.shopping_cart:
    st.divider()
    # ... (呢部分同之前一樣，保持顯示清單同計數)
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 計算與折扣
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    f_total = df_cart[df_cart['Category'].str.contains("Food")]['Price'].sum() * mult
    h_total = df_cart[df_cart['Category'].str.contains("Household")]['Price'].sum() * mult

    st.divider()
    st.metric("Food 🍏", f"${f_total:.2f}")
    st.metric("Household 🧻", f"${h_total:.2f}")
    st.info(f"### 總額: ${f_total + h_total:.2f}")

    if st.button("💾 儲存並更新記憶庫", type="primary", use_container_width=True):
        try:
            # 儲存前確保 Sheet 裡面嘅 Item 亦係統一樣式
            old_df = conn.read(worksheet="Sheet1")
            new_entries = df_cart[['Item', 'Category']].copy()
            # 統一寫入 Google Sheet 嘅格式 (第一個字大寫)
            new_entries['Item'] = new_entries['Item'].str.title()
            
            combined_df = pd.concat([old_df, new_entries]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=combined_df)
            st.success("✅ 儲存成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
