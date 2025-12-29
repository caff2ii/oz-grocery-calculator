import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 設定 ---
st.set_page_config(page_title="OZ Grocery Pro v2.7", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        if df is not None and not df.empty:
            # 確保 Item 名稱統一轉成大寫方便比對
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

history_dict = load_data()
options = ["+ 新增項目"] + sorted([str(k).title() for k in history_dict.keys()])

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

st.title("🛒 超市助手 v2.7")

# --- 2. 核心輸入區 ---
# 用 reset_count 確保加入清單後完全清空
current_key = f"item_select_{st.session_state.reset_count}"

selected_item = st.selectbox(
    "1. 搜尋或選擇項目:", 
    options=options,
    key=current_key
)

# 【關鍵修正】即時計算預測分類
if selected_item == "+ 新增項目" or not selected_item:
    final_name = st.text_input("輸入新項目名稱:", key=f"manual_{st.session_state.reset_count}").strip()
    pred_cat = "Food 🍏"
else:
    final_name = selected_item
    # 喺字典搵返對應嘅分類
    pred_cat = history_dict.get(selected_item.upper(), "Food 🍏")

st.divider()

col_p, col_c = st.columns(2)

with col_c:
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    
    # 搵出 pred_cat 喺 options 入面嘅位置
    if pred_cat in cat_options:
        target_index = cat_options.index(pred_cat)
    else:
        target_index = 0

    # 顯示分類格：使用動態 index 確保連動
    category = st.selectbox(
        "2. 分類:",
        options=cat_options,
        index=target_index,
        key=f"cat_select_{st.session_state.reset_count}_{selected_item}" # 加入 selected_item 作為 key 嘅一部分強制刷新
    )

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", step=0.01, key=f"price_{st.session_state.reset_count}")

# --- 3. 加入清單 Logic ---
if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if final_name and price > 0:
        st.session_state.shopping_cart.append({
            "Item": final_name.title(),
            "Price": price,
            "Category": category
        })
        st.session_state.reset_count += 1
        st.rerun()
    else:
        st.warning("⚠️ 請填寫名稱同金額")

# --- 4. 顯示清單與統計 ---
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
    mult = (100 - discount_pct) / 100

    # 分類統計
    food_total = df_cart[df_cart["Category"] == "Food 🍏"]["Price"].sum() * mult
    house_total = df_cart[df_cart["Category"] == "Household 🧻"]["Price"].sum() * mult
    other_total = df_cart[df_cart["Category"] == "Other 📦"]["Price"].sum() * mult
    grand_total = food_total + house_total + other_total

    st.write("### 📊 結帳小計")
    col1, col2 = st.columns(2)
    col1.metric("Food 🍏 (折後)", f"${food_total:.2f}")
    col2.metric("Household 🧻 (折後)", f"${house_total:.2f}")
    
    st.success(f"## 應付總額: ${grand_total:.2f}")

    if st.button("💾 儲存並同步", use_container_width=True):
        try:
            old_df = conn.read(worksheet="Sheet1")
            updated_df = pd.concat([old_df, df_cart[["Item", "Category"]]]).drop_duplicates(subset=["Item"], keep='last')
            conn.update(worksheet="Sheet1", data=updated_df)
            st.toast("✅ 同步成功！")
            st.cache_data.clear()
        except:
            st.error("儲存失敗")
