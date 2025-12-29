import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v1.6", layout="centered")

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
    st.session_state.random_id = str(random.randint(100000, 999999))

# --- 2. 邏輯函數 ---
def add_to_cart():
    # 獲取當前 widget 的值
    name = st.session_state.name_input.strip()
    price = st.session_state.price_input
    cat = st.session_state.cat_input
    
    if name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": name.title(),
            "Price": price,
            "Category": cat
        })
        # 清空並強制重新生成 ID 阻斷瀏覽器記憶
        st.session_state.item_to_fill = ""
        st.session_state.random_id = str(random.randint(100000, 999999))
        st.rerun()

# --- 3. 介面 (UI) ---
st.title("🛒 澳洲超市助手 v1.6")

# 這裡我們用 placeholder 確保建議區塊永遠在輸入框「正下方」
input_container = st.container()
suggestion_container = st.empty() # 👈 關鍵：用來即時刷新的容器

with input_container:
    # 移除關鍵字搜尋的延遲感：
    # 雖然 Streamlit 原生 text_input 依然需要 Enter 或 Tab 觸發，
    # 但我哋可以透過佈局讓它看起來更直覺。
    name_val = st.text_input(
        "1. 輸入項目:", 
        value=st.session_state.item_to_fill,
        key="name_input",
        placeholder="打完名撳 Tab 或 Enter 睇建議",
        autocomplete="new-password" # 👈 雙重保險停用 Chrome Autocomplete
    )

# --- 真正即時渲染建議 ---
# 只要 name_val 變動，呢個 container 會即刻重新整理
with suggestion_container:
    if name_val:
        search_term = name_val.upper()
        matches = [m for m in memory_dict.keys() if search_term in m][:3]
        
        if matches:
            st.write("✨ **你係咪搵緊：**")
            cols = st.columns(len(matches))
            for idx, m in enumerate(matches):
                # 點擊建議掣會直接填入並 rerun
                if cols[idx].button(f"🛒 {m.title()}", key=f"sug_{idx}_{st.session_state.random_id}", use_container_width=True):
                    st.session_state.item_to_fill = m.title()
                    st.rerun()

st.divider()

# 分類與金額
col_p, col_c = st.columns(2)

with col_c:
    current_upper = name_val.strip().upper()
    pred_cat = memory_dict.get(current_upper, "Food 🍏")
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    
    st.selectbox(
        "2. 分類:", 
        options=cat_options,
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0,
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

if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    add_to_cart()

# --- 4. 清單顯示 (保持 v1.5 的簡潔) ---
if st.session_state.shopping_cart:
    st.divider()
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}**")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 總額計算
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    total = sum(x['Price'] for x in st.session_state.shopping_cart) * mult
    st.success(f"### 應付總額: ${total:.2f}")

    if st.button("💾 儲存記憶庫", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = pd.DataFrame(st.session_state.shopping_cart)[['Item', 'Category']]
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 同步成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
