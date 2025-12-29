import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="OZ Grocery Forever Memory")

# --- 1. 連接 Google Sheets ---
# 注意：你需要喺 Streamlit Cloud 的 Secrets 設定中加入 Google Sheet URL
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取現有的記憶
@st.cache_data(ttl=60) # 每分鐘更新一次
def load_memory():
    try:
        return conn.read(worksheet="Sheet1")
    except:
        return pd.DataFrame(columns=["Item", "Category"])

memory_df = load_memory()
memory_dict = pd.Series(memory_df.Category.values, index=memory_df.Item.values).to_dict()

# --- 2. 介面 ---
st.title("🇦🇺 永久記憶分類計數機")

# 折扣設定
discount = st.number_input("Discount % OFF (e.g. 10)", 0, 100, 0)

# 互動表格
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame([{"Item": "", "Price": 0.0, "Category": "Other 📦"}])

def update_categories():
    for idx, row in st.session_state.df.iterrows():
        name = str(row['Item']).upper().strip()
        if name in memory_dict:
            st.session_state.df.at[idx, 'Category'] = memory_dict[name]

# 顯示編輯表格
edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)

# --- 3. 儲存新記憶 ---
if st.button("💾 儲存並記住新項目"):
    new_memory_entries = []
    for _, row in edited_df.iterrows():
        item = str(row['Item']).upper().strip()
        if item and item not in memory_dict:
            new_memory_entries.append({"Item": item, "Category": row['Category']})
    
    if new_memory_entries:
        updated_df = pd.concat([memory_df, pd.DataFrame(new_memory_entries)], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("記憶已更新到 Google Sheets！")
        st.cache_data.clear() # 清除 Cache 以讀取新數據
    else:
        st.info("冇新項目需要記住。")

# --- 4. 計算折扣金額 ---
mult = (100 - discount) / 100
food_total = edited_df[edited_df['Category'].str.contains("Food")]['Price'].sum() * mult
house_total = edited_df[edited_df['Category'].str.contains("Household")]['Price'].sum() * mult

st.divider()
st.subheader(f"Total (After {discount}% Off)")
st.write(f"🍏 Food: **${food_total:.2f}**")
st.write(f"🧻 Household: **${house_total:.2f}**")
st.write(f"💰 Total: **${food_total + house_total:.2f}**")
