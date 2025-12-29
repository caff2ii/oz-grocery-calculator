import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 設定 ---
st.set_page_config(page_title="OZ Grocery Pro v2.8", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        if df is not None and not df.empty:
            # 統一存儲大寫 key 方便對比
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

history_dict = load_data()

# --- 關鍵改動：預設選項係空白 ---
# 排列：空白 -> + 新增項目 -> 歷史紀錄
options = ["", "+ 新增項目"] + sorted([str(k).title() for k in history_dict.keys()])

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

st.title("🛒 超市助手 v2.8")

# --- 2. 核心輸入區 ---
# 每次 reset_count 增加，selectbox 會跳返去 index=0 (即係 "")
current_key = f"item_select_{st.session_state.reset_count}"

selected_item = st.selectbox(
    "1. 搜尋項目 (直接打字):", 
    options=options,
    index=0, # 預設選中第一個選項，即係 ""
    key=current_key
)

# 判定名稱
final_name = ""
pred_cat = "Food 🍏"

if selected_item == "+ 新增項目":
    final_name = st.text_input("輸入新項目名稱:", key=f"manual_{st.session_state.reset_count}").strip()
elif selected_item != "":
    final_name = selected_item
    pred_cat = history_dict.get(selected_item.upper(), "Food 🍏")

st.divider()

col_p, col_c = st.columns(2)

with col_c:
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    target_index = cat_options.index(pred_cat) if pred_cat in cat_options else 0

    # 連動分類：當 selected_item 變動時，呢個格會重新生成
    category = st.selectbox(
        "2. 分類:",
        options=cat_options,
        index=target_index,
        key=f"cat_{st.session_state.reset_count}_{selected_item}"
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
        # 增加 reset_count 令所有格變返初始狀態
        st.session_state.reset_count += 1
        st.rerun()
    else:
        st.warning("⚠️ 請填寫名稱同金額")

# --- 4. 顯示清單與統計 (維持 v2.7 邏輯) ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    
    for i, item in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{item['Item']}**")
        c2.write(f"${item['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    st.divider()
    discount_pct = st.number_input("全單折扣 % OFF:", 0, 100, 0, 5)
    mult = (100 - discount_pct) / 100

    food_total = df_cart[df_cart["Category"] == "Food 🍏"]["Price"].sum() * mult
    house_total = df_cart[df_cart["Category"] == "Household 🧻"]["Price"].sum() * mult
    grand_total = (df_cart["Price"].sum()) * mult

    st.write("### 📊 結帳小計")
    col1, col2 = st.columns(2)
    col1.metric("Food 🍏", f"${food_total:.2f}")
    col2.metric("Household 🧻", f"${house_total:.2f}")
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
