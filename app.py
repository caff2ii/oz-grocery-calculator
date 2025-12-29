import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Easy Input", layout="centered")

# --- 1. 初始化與數據讀取 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        # 轉為 Dictionary 方便搵分類
        h_dict = pd.Series(df.Category.values, index=df.Item.values).to_dict()
        h_list = sorted(df.Item.unique().tolist())
        return h_dict, h_list
    except:
        return {}, []

history_dict, history_list = load_data()

# --- 2. 狀態管理 (儲存目前買緊嘅清單) ---
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

# --- 3. 輸入 Field 區域 ---
st.title("🛒 澳洲超市計數機")

with st.container():
    st.subheader("新增項目")
    
    # Dropdown Menu (可以打字 Search)
    selected_item = st.selectbox(
        "搜尋舊項目:",
        options=[""] + history_list,
        format_func=lambda x: "--- 揀選已有項目 ---" if x == "" else x
    )
    
    # 如果 Dropdown 冇，就用呢個 Field 手打
    new_item = st.text_input("或手打新項目名稱:", placeholder="e.g. Probiotics")
    
    # 最終決定用邊個名
    final_item_name = new_item if new_item else selected_item
    
    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        # 自動搵返舊分類，搵唔到就預設 Food
        suggested_cat = history_dict.get(final_item_name, "Food 🍏")
        category = st.selectbox("分類:", ["Food 🍏", "Household 🧻", "Other 📦"], 
                               index=["Food 🍏", "Household 🧻", "Other 📦"].index(suggested_cat))

    if st.button("➕ 加入清單", use_container_width=True):
        if final_item_name and price > 0:
            st.session_state.shopping_cart.append({
                "Item": final_item_name,
                "Price": price,
                "Category": category
            })
            st.success(f"已加入 {final_item_name}")
            st.rerun() # 重新整理清空輸入框
        else:
            st.warning("請輸入名稱同金額！")

# --- 4. 顯示已加入清單 (預覽區) ---
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

    # --- 5. 計算區 (含折扣) ---
    st.divider()
    discount_pct = st.number_input("全單折扣 % OFF (例如 10)", 0, 100, 0)
    multiplier = (100 - discount_pct) / 100

    food_total = sum(item['Price'] for item in st.session_state.shopping_cart if "Food" in item['Category']) * multiplier
    house_total = sum(item['Price'] for item in st.session_state.shopping_cart if "Household" in item['Category']) * multiplier

    st.subheader("📊 總額預計")
    col_f, col_h = st.columns(2)
    col_f.metric("Food Total", f"${food_total:.2f}")
    col_h.metric("Household Total", f"${house_total:.2f}")
    
    final_total = food_total + house_total
    st.info(f"💰 折扣後總共要俾: **${final_total:.2f}**")

    # --- 6. 永久記憶儲存 ---
    if st.button("💾 記住新項目 (永久記憶)", use_container_width=True):
        # 讀取現有，合併新嘢，Save 去 Google Sheets
        current_df = pd.DataFrame(st.session_state.shopping_cart)[['Item', 'Category']]
        existing_df = conn.read(worksheet="Sheet1")
        # 去重，保留最新分類
        updated_df = pd.concat([existing_df, current_df]).drop_duplicates(subset=['Item'], keep='last')
        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("記憶成功！下次 Dropdown 就會見到。")
        st.cache_data.clear()
else:
    st.info("清單仲係空嘅，快啲入嘢啦！")
