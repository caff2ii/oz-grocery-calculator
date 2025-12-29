import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_searchbox import st_searchbox

st.set_page_config(page_title="OZ Grocery Pro", layout="centered")

# --- 1. 初始化與讀取 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        h_dict = pd.Series(df.Category.values, index=df.Item.values).to_dict()
        h_list = sorted(df.Item.unique().tolist())
        return h_dict, h_list
    except:
        return {}, []

history_dict, history_list = load_data()

# 定義搜尋函數：喺舊紀錄入面搵返匹配嘅字
def search_items(search_term: str):
    if not search_term:
        return []
    return [item for item in history_list if search_term.lower() in item.lower()]

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

# --- 2. 輸入區 ---
st.title("🛒 澳洲超市智能助手")

with st.container():
    st.subheader("新增項目")
    
    # 呢個就係你要嘅：邊打邊彈建議，冇就直接輸入
    final_item_name = st_searchbox(
        search_items,
        placeholder="打字搵舊嘢，或直接打新名...",
        key="grocery_search",
    )
    
    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        # 當你揀好咗/打好咗名，自動幫你對返個分類
        suggested_cat = history_dict.get(final_item_name, "Food 🍏")
        cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
        category = st.selectbox("分類:", cat_options, index=cat_options.index(suggested_cat))

    if st.button("➕ 加入清單", use_container_width=True):
        if final_item_name and price > 0:
            st.session_state.shopping_cart.append({
                "Item": final_item_name,
                "Price": price,
                "Category": category
            })
            st.rerun()

# --- 3. 預覽清單 ---
st.divider()
if st.session_state.shopping_cart:
    st.subheader("目前清單")
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # --- 4. 折扣與計算 ---
    st.divider()
    discount_pct = st.number_input("全單折扣 % OFF (例如 10)", 0, 100, 0)
    multiplier = (100 - discount_pct) / 100

    food_total = sum(item['Price'] for item in st.session_state.shopping_cart if "Food" in item['Category']) * multiplier
    house_total = sum(item['Price'] for item in st.session_state.shopping_cart if "Household" in item['Category']) * multiplier

    st.subheader("📊 總計 (折扣後)")
    col_f, col_h = st.columns(2)
    col_f.metric("Food 🍏", f"${food_total:.2f}")
    col_h.metric("Household 🧻", f"${house_total:.2f}")
    st.info(f"💰 全單總額: **${food_total + house_total:.2f}**")

    # --- 5. 永久記憶 ---
    if st.button("💾 記住新項目到 Google Sheets", use_container_width=True):
        current_items = pd.DataFrame(st.session_state.shopping_cart)[['Item', 'Category']]
        existing_df = conn.read(worksheet="Sheet1")
        updated_df = pd.concat([existing_df, current_items]).drop_duplicates(subset=['Item'], keep='last')
        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("記憶已更新！下次打字會有建議。")
        st.cache_data.clear()
else:
    st.info("快啲加嘢落清單啦！")
