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
# 將舊項目排列好，並加個「新增」喺頂
options = ["+ 新增項目"] + sorted(list(history_dict.keys()))

# 初始化購物車
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 超市助手 v2.1")

# --- 2. 搜尋與輸入區 ---
# 用 Selectbox 解決 Safari/Chrome Autocomplete 遮擋問題
selected_item = st.selectbox(
    "1. 搜尋或選擇項目 (打字即 Filter):",
    options=options,
    index=0
)

# 邏輯判斷：新項目定舊項目
if selected_item == "+ 新增項目":
    # 只有揀新增，先至彈個 input box
    final_name = st.text_input("輸入新項目名稱:", placeholder="例如: Milk").strip()
    pred_cat = "Food 🍏"
else:
    final_name = selected_item
    pred_cat = history_dict.get(selected_item, "Food 🍏")

st.divider()

# --- 3. 金額與分類 ---
col_p, col_c = st.columns(2)

with col_c:
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    # 根據選中嘅項目自動跳轉分類
    category = st.selectbox(
        "2. 分類:",
        options=cat_options,
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0
    )

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01)

# --- 4. 加入清單 ---
if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": final_name.title(),
            "Price": price,
            "Category": category
        })
        st.rerun()
    else:
        st.warning("⚠️ 請填寫名稱同金額")

# --- 5. 顯示結果與儲存 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    # 清單列表
    for i, item in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{item['Item']}** ({item['Category']})")
        c2.write(f"${item['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 折扣與統計
    st.divider()
    discount_pct = st.number_input("全單折扣 % OFF:", 0, 100, 0)
    multiplier = (100 - discount_pct) / 100
    
    total_raw = df_cart["Price"].sum()
    total_discounted = total_raw * multiplier
    
    st.success(f"### 應付總額: ${total_discounted:.2f}")
    if discount_pct > 0:
        st.caption(f"(原價: ${total_raw:.2f})")

    # 儲存回 Google Sheets
    if st.button("💾 儲存並同步雲端記憶庫", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[["Item", "Category"]].copy()
            # 合併新舊數據，如果有重覆 Item，以最新一次分類為準
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=["Item"], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 雲端同步完成！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
