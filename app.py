import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 初始化 Google Sheets 連接
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取「記憶資料庫」(之前買過嘅嘢)
@st.cache_data(ttl=60)
def get_historical_items():
    try:
        df = conn.read(worksheet="Sheet1")
        # 轉成 Dictionary 方便搵分類，同埋一個 List 方便做 Suggestion
        history_dict = pd.Series(df.Category.values, index=df.Item.values).to_dict()
        history_list = df.Item.unique().tolist()
        return history_dict, history_list
    except:
        return {}, []

history_dict, history_list = get_historical_items()

# 3. 介面
st.title("🇦🇺 智能建議分類計數機")

# 4. 輸入區 (加入 Autocomplete)
st.subheader("輸入項目")

# 我哋用一個表格編輯器，但針對 "Item" 嗰行加入建議
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame([{"Item": "", "Price": 0.0, "Category": "Food 🍏"}])

# 設定表格：Item 呢一列會顯示建議
edited_df = st.data_editor(
    st.session_state.data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Item": st.column_config.SelectboxColumn(
            "Item (可搜尋建議)",
            help="輸入關鍵字會自動過濾之前買過嘅嘢",
            options=history_list, # 呢度就係你之前入過嘅 Probiotics 等等
            required=True
        ),
        "Category": st.column_config.SelectboxColumn(
            "Category",
            options=["Food 🍏", "Household 🧻", "Other 📦"]
        )
    }
)

# 5. 當你揀咗一個舊 Item，自動幫你填返個 Category
for idx, row in edited_df.iterrows():
    name = row['Item']
    if name in history_dict:
        # 如果用戶揀咗建議嘅 Item，自動對應返佢之前嘅分類
        edited_df.at[idx, 'Category'] = history_dict[name]

# 6. 折扣與計算 (同之前一樣)
discount = st.number_input("Discount %", 0, 100, 0)
mult = (100 - discount) / 100

food_total = edited_df[edited_df['Category'].str.contains("Food")]['Price'].sum() * mult
house_total = edited_df[edited_df['Category'].str.contains("Household")]['Price'].sum() * mult

st.divider()
st.metric("Total Food (After Discount)", f"${food_total:.2f}")
st.metric("Total Household (After Discount)", f"${house_total:.2f}")

# 7. 儲存新 Item 到記憶
if st.button("💾 記住新項目 (下次會有建議)"):
    # 呢度寫入 Google Sheets 嘅 logic...
    st.success("已記住，下次輸入會彈出建議！")
