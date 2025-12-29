import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 基本設定 ---
st.set_page_config(page_title="OZ Grocery Pro v2.5", layout="centered")

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

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 超市助手 v2.5")

# --- 2. 輸入區 ---
selected_item = st.selectbox("1. 搜尋或選擇項目:", options=options)

if selected_item == "+ 新增項目":
    final_name = st.text_input("輸入新項目名稱:", key="manual_name").strip()
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
        index=cat_options.index(pred_cat) if pred_cat in cat_options else 0
    )

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01)

if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": final_name.title(),
            "Price": price,
            "Category": category
        })
        st.rerun()

# --- 3. 購物清單與計算區 ---
if st.session_state.shopping_cart:
    st.divider()
    st.subheader("📝 目前清單")
    
    # 建立 DataFrame 方便計算
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    # 顯示清單並提供刪除按鈕
    for i, item in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{item['Item']}** ({item['Category']})")
        c2.write(f"${item['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    st.divider()

    # --- 折扣輸入 ---
    # 例如：超市常見的 10% OFF 或 Half Price
    discount_pct = st.number_input("全單折扣 (例如打 9 折請入 10% OFF):", min_value=0, max_value=100, value=0, step=5)
    multiplier = (100 - discount_pct) / 100

    # --- 分類小計 ---
    # 分開 Food 同 Household 計算
    food_subtotal = df_cart[df_cart["Category"] == "Food 🍏"]["Price"].sum() * multiplier
    house_subtotal = df_cart[df_cart["Category"] == "Household 🧻"]["Price"].sum() * multiplier
    other_subtotal = df_cart[df_cart["Category"] == "Other 📦"]["Price"].sum() * multiplier
    
    total_final = food_subtotal + house_subtotal + other_subtotal

    # 顯示統計結果
    st.write("### 📊 結帳小計")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Food 🍏 (折後)", f"${food_subtotal:.2f}")
    with col2:
        st.metric("Household 🧻 (折後)", f"${house_subtotal:.2f}")
    
    if other_subtotal > 0:
        st.write(f"Other 📦: ${other_subtotal:.2f}")

    st.success(f"## 應付總額: ${total_final:.2f}")

    # --- 4. 儲存功能 ---
    if st.button("💾 儲存記憶並同步雲端", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            new_data = df_cart[["Item", "Category"]].copy()
            updated_df = pd.concat([old_df, new_data]).drop_duplicates(subset=["Item"], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 雲端同步完成！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
