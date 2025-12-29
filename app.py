import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro", layout="wide")

# --- 1. 初始化記憶與連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_all_memory():
    try:
        df = conn.read(worksheet="Sheet1")
        # 轉為 Dictionary: {'MILK': 'Food 🍏'}
        d = pd.Series(df.Category.values, index=df.Item.values).to_dict()
        l = df.Item.unique().tolist()
        return d, l
    except:
        return {}, []

history_dict, history_list = load_all_memory()

# --- 2. 處理數據狀態 (防止重整時數據消失) ---
if "df_value" not in st.session_state:
    st.session_state.df_value = pd.DataFrame([{"Item": "", "Price": 0.0, "Category": "Food 🍏"}])

# --- 3. 介面 ---
st.title("🇦🇺 澳洲超市智能清單")

# 折扣設定 (擺喺外面費事 rerun)
discount = st.number_input("Discount % OFF (e.g. 10)", 0, 100, 0)

# --- 4. 核心：Data Editor ---
# 我哋將結果放入 edited_df
edited_df = st.data_editor(
    st.session_state.df_value,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Item": st.column_config.SelectboxColumn(
            "Item (可輸入或選擇建議)",
            options=history_list,  # 呢度顯示建議
            required=True,
        ),
        "Category": st.column_config.SelectboxColumn(
            "Category",
            options=["Food 🍏", "Household 🧻", "Other 📦"]
        )
    },
    key="my_editor" # 加入固定 Key 令狀態更穩定
)

# --- 5. 自動填寫分類邏輯 ---
# 檢查有沒有剛揀好的 Item，如果有且在記憶中，自動幫佢轉 Category
for idx, row in edited_df.iterrows():
    name = row['Item']
    if name in history_dict:
        # 只在 Category 還是預設時才自動更改，避免覆蓋用戶手動修改
        if edited_df.at[idx, 'Category'] != history_dict[name]:
            edited_df.at[idx, 'Category'] = history_dict[name]

# --- 6. 計算金額 ---
mult = (100 - discount) / 100
food_total = edited_df[edited_df['Category'].str.contains("Food")]['Price'].sum() * mult
house_total = edited_df[edited_df['Category'].str.contains("Household")]['Price'].sum() * mult

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Food 🍏", f"${food_total:.2f}")
c2.metric("Household 🧻", f"${house_total:.2f}")
c3.metric("Total 💰", f"${food_total + house_total:.2f}")

# --- 7. 儲存按鈕 ---
if st.button("💾 記住所有新 Item (下次自動彈出)"):
    # 這裡加入寫入 Google Sheets 的邏輯
    # ... (conn.update ...)
    st.success("記憶已更新！")
    st.cache_data.clear()
