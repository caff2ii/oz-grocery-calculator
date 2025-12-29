import streamlit as st
import pandas as pd

# 1. 基本設定
st.set_page_config(page_title="OZ Grocery Fix", layout="centered")

# 從 Secrets 獲取連結 (請確保 Secrets 入面 spreadsheet 條 link 係啱嘅)
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # 將網址轉換為直接下載 CSV 嘅格式
    CSV_URL = SHEET_URL.replace('/edit#gid=', '/export?format=csv&gid=').replace('/edit?usp=sharing', '/export?format=csv')
except:
    st.error("❌ 搵唔到 Secrets 入面嘅 spreadsheet 連結，請檢查 Streamlit Secrets 設定。")
    st.stop()

# 2. 讀取記憶功能 (直接用 pandas)
@st.cache_data(ttl=5)
def load_memory():
    try:
        # 直接由 Google Sheet 下載 CSV
        df = pd.read_csv(CSV_URL)
        if not df.empty and 'Item' in df.columns:
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except:
        return {}

memory_dict = load_memory()

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市計數機 (修復版)")

# 3. 輸入 Form
with st.form(key="my_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        item = st.text_input("項目名稱:")
    with col2:
        price = st.number_input("金額:", min_value=0.0, format="%.2f")
    
    cat = st.selectbox("分類:", ["Food 🍏", "Household 🧻", "Other 📦"])
    submit = st.form_submit_button("加入清單")

    if submit and item:
        # 智能分類
        final_cat = memory_dict.get(item.strip().upper(), cat)
        st.session_state.shopping_cart.append({"Item": item, "Price": price, "Category": final_cat})
        st.rerun()

# 4. 顯示清單
if st.session_state.shopping_cart:
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    for i, row in df_cart.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"{row['Item']} ({row['Category']})")
        c2.write(f"${row['Price']:.2f}")
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.shopping_cart.pop(i)
            st.rerun()

    # 5. 計算
    discount = st.number_input("折扣 % OFF:", 0, 100, 0)
    mult = (100 - discount) / 100
    
    food = df_cart[df_cart['Category'].str.contains("Food")]['Price'].sum() * mult
    house = df_cart[df_cart['Category'].str.contains("Household")]['Price'].sum() * mult
    
    st.divider()
    st.metric("Food 🍏", f"${food:.2f}")
    st.metric("Household 🧻", f"${house:.2f}")
    st.success(f"總額: ${food + house:.2f}")

    # 6. 儲存功能 (呢度我哋用返 st.connection 嘅 update，因為讀取最易出 400，寫入通常冇事)
    if st.button("💾 儲存到 Google Sheets", type="primary"):
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            # 讀取現有
            old_df = pd.read_csv(CSV_URL)
            new_df = pd.concat([old_df, df_cart[['Item', 'Category']]]).drop_duplicates(subset=['Item'], keep='last')
            conn.update(worksheet="Sheet1", data=new_df)
            st.toast("✅ 儲存成功！")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"儲存失敗: {e}")
