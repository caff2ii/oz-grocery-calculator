import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v1.4", layout="centered")

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
if "input_key" not in st.session_state:
    st.session_state.input_key = str(random.randint(1000, 9999))

# --- 2. 邏輯函數 ---
def add_to_cart():
    # 攞依家畫面格入面嘅數值
    name = st.session_state.name_input.strip()
    price = st.session_state.price_input
    cat = st.session_state.cat_input
    
    if name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": name.title(),
            "Price": price,
            "Category": cat
        })
        # 清空並更換 Key，令 Safari 以為係新輸入框，停用自動完成
        st.session_state.item_to_fill = ""
        st.session_state.input_key = str(random.randint(1000, 9999))
        st.rerun()
    else:
        st.toast("⚠️ 請輸入名稱同價錢")

# --- 3. 介面 (UI) ---
st.title("🛒 澳洲超市助手 v1.4")

# 利用隨機 Key 嚟避開 Safari 嘅自動完成 (Autocomplete)
name_val = st.text_input(
    "1. 項目名稱:", 
    value=st.session_state.item_to_fill,
    key="name_input",
    help="打字即出建議",
    placeholder="在此輸入項目名稱"
)

# --- 即時 Suggestion 區 (無需 Enter，即打即現) ---
if name_val:
    search_term = name_val.upper()
    matches = [m for m in memory_dict.keys() if search_term in m][:3]
    
    if matches:
        st.caption("🔍 建議項目 (點擊填入):")
        cols = st.columns(len(matches))
        for idx, m in enumerate(matches):
            if cols[idx].button(f"✨ {m.title()}", key=f"sug_{idx}_{st.session_state.input_key}", use_container_width=True):
                st.session_state.item_to_fill = m.title()
                st.rerun()

st.divider()

# 分類與金額
col_p, col_c = st.columns(2)

with col_c:
    # 智能預測：如果係買過嘅嘢，自動跳去嗰個分類，但仲可以手動改
    current_upper = name_val.strip().upper()
    pred_cat = memory_dict.get(current_upper, "Food 🍏")
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    
    selected_cat = st.selectbox(
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

# 加入按鈕 (因為唔用 on_change 費事誤觸，我哋用一個大按鈕)
if st.button("➕ 加入清單 (撳 Enter 亦可)", use_container_width=True, type="primary"):
    add_to_cart()

# --- 4. 清單顯示與計算 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    # 顯示目前清單 (用 Markdown 靚少少)
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 計算折扣
    st.divider()
    discount = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    multiplier = (100 - discount) / 100
    
    f_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * multiplier
    h_total = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * multiplier

    st.success(f"### 應付總額: ${f_total + h_total:.2f}")
    st.caption(f"(Food: ${f_total:.2f} | Household: ${h_total:.2f})")

    # 儲存
    if st.button("💾 儲存並更新記憶庫", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[['Item', 'Category']].copy()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 儲存成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
