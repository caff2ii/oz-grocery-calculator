import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro", layout="centered")

# --- 1. 初始化與數據讀取 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1")
        h_dict = pd.Series(df.Category.values, index=df.Item.values).to_dict()
        return h_dict
    except:
        return {}

history_dict = load_data()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市智能助手")

# --- 2. 輸入區域 ---
with st.form(key="input_form", clear_on_submit=True):
    st.subheader("新增項目")
    item_name = st.text_input("項目名稱 (e.g. Milk):").strip()
    
    # 預測分類
    suggested_cat = history_dict.get(item_name, "Food 🍏")
    
    col_p, col_c = st.columns(2)
    with col_p:
        price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")
    with col_c:
        cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
        idx = cat_options.index(suggested_cat) if suggested_cat in cat_options else 0
        category = st.selectbox("分類:", cat_options, index=idx)

    submit_button = st.form_submit_button("➕ 加入清單 (Enter)", use_container_width=True)

    if submit_button:
        if item_name and price > 0:
            st.session_state.shopping_cart.append({
                "Item": item_name,
                "Price": price,
                "Category": category
            })
            st.rerun()

# --- 3. 顯示清單與即時計算 ---
if st.session_state.shopping_cart:
    st.divider()
    st.subheader("📋 目前清單")
    
    # 建立表格顯示
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{entry['Item']}** ({entry['Category']})")
        c2.write(f"${entry['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # --- 4. 計算與折扣區 ---
    st.divider()
    st.subheader("💰 結算金額")
    
    discount_pct = st.number_input("全單折扣 % OFF (例如 10% 填 10)", 0, 100, 0)
    multiplier = (100 - discount_pct) / 100

    # 分類計數
    food_total = sum(item['Price'] for item in st.session_state.shopping_cart if "Food" in item['Category']) * multiplier
    house_total = sum(item['Price'] for item in st.session_state.shopping_cart if "Household" in item['Category']) * multiplier
    grand_total = food_total + house_total

    col_f, col_h = st.columns(2)
    col_f.metric("Food (折後)", f"${food_total:.2f}")
    col_h.metric("Household (折後)", f"${house_total:.2f}")
    
    st.info(f"### 總共要俾: **${grand_total:.2f}**")

    # --- 5. 永久記憶按鈕 (最重要) ---
    st.write("---")
    if st.button("💾 將新項目記落 Google Sheets", use_container_width=True, type="primary"):
        with st.spinner('儲存記憶中...'):
            current_df = pd.DataFrame(st.session_state.shopping_cart)[['Item', 'Category']]
            try:
                # 讀取現有的，合併並去重
                existing_df = conn.read(worksheet="Sheet1")
                updated_df = pd.concat([existing_df, current_df]).drop_duplicates(subset=['Item'], keep='last')
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("✅ 記憶成功！下次買呢啲嘢會自動填分類。")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"儲存失敗，請檢查 Google Sheets 權限。詳情: {e}")
else:
    st.info("清單係空嘅，請喺上面輸入項目。")
