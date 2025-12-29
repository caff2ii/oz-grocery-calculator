import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v2.1", layout="centered")

# 連接 Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        if not df.empty:
            # 整理成字典 {項目名: 分類}
            return pd.Series(df.Category.values, index=df.Item.values).to_dict()
        return {}
    except:
        return {}

history_dict = load_data()
# 攞出所有舊項目名，加個「+ 新增項目」喺最頂
options = ["+ 新增項目"] + sorted(list(history_dict.keys()))

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 超市助手 v2.1")

# --- 2. 核心：用 Selectbox 代替 TextInput ---
# Selectbox 喺手機會彈出原生選單，打字可以即時 Filter，而且絕對唔會出 Safari/Chrome 嘅舊紀錄
selected_item = st.selectbox(
    "1. 搜尋或選擇項目:",
    options=options,
    index=0,
    help="直接打字可以快速搜尋舊項目"
)

# 如果揀咗「新增項目」，先至彈個格畀你打新名
if selected_item == "+ 新增項目":
    final_name = st.text_input("輸入新項目名稱:", key="new_item_name", placeholder="例如: Milk").strip()
    pred_cat = "Food 🍏"
else:
    final_name = selected_item
    pred_cat = history_dict.get(selected_item, "Food 🍏")

st.divider()

# --- 3. 分類與金額 ---
col_p, col_c = st.columns(2)

with col_c:
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    # 如果係舊項目，會自動跳去對應分類
    category = st.selectbox(
        "2. 分類:",
        options=cat_options,
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0
    )

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01, key="price_input")

# --- 4. 加入邏輯 ---
if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": final_name.title(),
            "Price": price,
            "Category": category
        })
        st.rerun()
    else:
        st.error("請輸入名稱同價錢！")

# --- 5. 清單顯示與計算 (保持不變) ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    # 顯示清單並提供刪除按鈕
    for i, item in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{item['Item']}** ({item['Category']})")
        c2.write(f"${item['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    total = df_cart["Price"].sum()
    st.success(f"### 總額: ${total:.2f}")

    if st.button("💾 儲存記憶並上傳", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_entries = df_cart[["Item", "Category"]].copy()
            updated_df = pd.concat([old_df, new_entries]).drop_duplicates(subset=["Item"], keep="last")
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 已同步到 Google Sheets")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
