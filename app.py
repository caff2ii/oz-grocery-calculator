import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection

# --- 1. 設定 ---
st.set_page_config(page_title="OZ Grocery Pro v2.6", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        if df is not None and not df.empty:
            return pd.Series(df.Category.values, index=df.Item.values).to_dict()
        return {}
    except:
        return {}

history_dict = load_data()
options = ["+ 新增項目"] + sorted(list(history_dict.keys()))

# 初始化購物車同埋用於重置的 Reset Counter
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

# --- 2. 介面與輸入 ---
st.title("🛒 超市助手 v2.6")

# 關鍵：用 reset_count 嚟做 key 嘅一部分
# 只要 reset_count 一變，呢個 selectbox 就會變返初始狀態（清空搜尋）
current_key = f"item_select_{st.session_state.reset_count}"

selected_item = st.selectbox(
    "1. 搜尋或選擇項目:", 
    options=options,
    key=current_key
)

# 判定名稱同預設分類
if selected_item == "+ 新增項目":
    # 加多個 key 確保呢度都可以重置
    final_name = st.text_input("輸入新項目名稱:", key=f"manual_{st.session_state.reset_count}").strip()
    pred_cat = "Food 🍏"
else:
    final_name = selected_item
    pred_cat = history_dict.get(selected_item, "Food 🍏")

st.divider()

col_p, col_c = st.columns(2)
with col_c:
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    category = st.selectbox(
        "2. 分類:",
        options=cat_options,
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0,
        key=f"cat_select_{st.session_state.reset_count}"
    )

with col_p:
    # 金額格亦都跟住 reset
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01, key=f"price_{st.session_state.reset_count}")

# --- 3. 加入清單 Logic ---
if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_name and price > 0:
        # 加入購物車
        st.session_state.shopping_cart.append({
            "Item": final_name.title(),
            "Price": price,
            "Category": category
        })
        # 【核心改動】增加 reset_count，令上面所有 Widget 全部歸零
        st.session_state.reset_count += 1
        st.rerun()
    else:
        st.warning("⚠️ 請填寫名稱同金額")

# --- 4. 顯示清單、折扣與小計 (同 v2.5) ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    for i, item in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{item['Item']}** ({item['Category']})")
        c2.write(f"${item['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    st.divider()
    discount_pct = st.number_input("全單折扣 % OFF:", 0, 100, 0, 5)
    multiplier = (100 - discount_pct) / 100

    food_sub = df_cart[df_cart["Category"] == "Food 🍏"]["Price"].sum() * multiplier
    house_sub = df_cart[df_cart["Category"] == "Household 🧻"]["Price"].sum() * multiplier
    total = food_sub + house_sub + (df_cart[df_cart["Category"] == "Other 📦"]["Price"].sum() * multiplier)

    st.write("### 📊 結帳小計")
    col1, col2 = st.columns(2)
    col1.metric("Food 🍏", f"${food_sub:.2f}")
    col2.metric("Household 🧻", f"${house_sub:.2f}")
    st.success(f"## 應付總額: ${total:.2f}")

    if st.button("💾 儲存並同步", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            updated_df = pd.concat([old_df, df_cart[["Item", "Category"]]]).drop_duplicates(subset=["Item"], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 同步成功！")
            st.cache_data.clear()
        except:
            st.error("儲存失敗")
