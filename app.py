import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_searchbox import st_searchbox

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v2.0", layout="centered")

# 連接 Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        return df
    except:
        return pd.DataFrame(columns=["Item", "Category"])

df_history = load_data()

# 搜尋函數：searchbox 會自動傳入用戶打嘅字 (searchterm)
def search_items(searchterm: str):
    if not searchterm:
        return []
    # 搵出匹配嘅 Item，唔分大細楷
    matches = df_history[df_history["Item"].str.contains(searchterm, case=False, na=False)]
    # 回傳一個 List 畀選單顯示
    return matches["Item"].unique().tolist()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 超市助手 v2.0")

# --- 3. 核心組件：st_searchbox ---
# 呢個組件自帶即時聯想，打一個字就出建議，唔使撳 Enter
selected_item = st_searchbox(
    search_items,
    key="item_search",
    placeholder="🔍 搜尋或輸入項目名稱...",
    clear_on_submit=False, # 方便你睇返打咗咩
)

# 確保個名第一個字大寫
final_item_name = selected_item.title() if selected_item else ""

# --- 4. 自動連動分類 ---
col_p, col_c = st.columns(2)

with col_c:
    # 根據 searchbox 選中嘅嘢去搵分類
    if selected_item:
        match_row = df_history[df_history["Item"].str.upper() == selected_item.upper()]
        pred_cat = match_row["Category"].iloc[0] if not match_row.empty else "Food 🍏"
    else:
        pred_cat = "Food 🍏"
    
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    selected_cat = st.selectbox(
        "2. 分類:", 
        options=cat_options, 
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0
    )

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01)

# --- 5. 加入清單 ---
if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_item_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": final_item_name,
            "Price": price,
            "Category": selected_cat
        })
        st.rerun()

# --- 6. 顯示結果 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    st.dataframe(df_cart, use_container_width=True, hide_index=True)
    
    total = df_cart["Price"].sum()
    st.success(f"### 總額: ${total:.2f}")

    if st.button("💾 儲存並更新記憶庫", use_container_width=True):
        updated_df = pd.concat([df_history, df_cart[["Item", "Category"]]]).drop_duplicates(subset=["Item"], keep="last")
        conn.update(worksheet="Sheet1", data=updated_df)
        st.toast("✅ 儲存成功！")
        st.cache_data.clear()
