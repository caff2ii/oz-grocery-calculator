import streamlit as st
import pandas as pd

st.set_page_config(page_title="OZ Grocery Pro", layout="wide")

# --- 1. 初始化「記憶資料庫」 ---
if 'memory' not in st.session_state:
    # 預設一啲基本分類
    st.session_state.memory = {
        'MILK': 'Food 🍏',
        'BREAD': 'Food 🍏',
        'TOILET PAPER': 'Household 🧻',
        'PANADOL': 'Household 🧻'
    }

if 'rows' not in st.session_state:
    st.session_state.rows = [{"Item": "", "Price": 0.0, "Category": "Food 🍏"}]

# --- 2. 介面標題 ---
st.title("🇦🇺 Woolies/Coles 智能清單")
st.write("輸入 Item 會自動幫你記住分類，支持全單折扣計算。")

# --- 3. 折扣設定 ---
with st.sidebar:
    st.header("Settings")
    discount_pct = st.number_input("全單折扣 (例如 9折輸入 10%)", min_value=0, max_value=100, value=0)
    multiplier = (100 - discount_pct) / 100

# --- 4. 互動表格區 ---
st.subheader("清單內容")
# 使用 data_editor 讓你可以像 Excel 編輯
edited_df = st.data_editor(
    pd.DataFrame(st.session_state.rows),
    num_rows="dynamic",
    column_config={
        "Category": st.column_config.SelectboxColumn(
            options=["Food 🍏", "Household 🧻", "Other 📦"]
        )
    },
    use_container_width=True,
    key="editor"
)

# --- 5. 自動記憶分類邏輯 ---
# 檢查有沒有新輸入的 Item 並更新記憶
for index, row in edited_df.iterrows():
    item_name = str(row['Item']).upper().strip()
    if item_name:
        if item_name in st.session_state.memory:
            # 如果記憶中有，自動更新當前表格的分類 (這部分在 UI 體驗上會稍後反應)
            edited_df.at[index, 'Category'] = st.session_state.memory[item_name]
        else:
            # 如果是新分類，記住它
            st.session_state.memory[item_name] = row['Category']

# --- 6. 計算結果 ---
st.divider()
col1, col2, col3 = st.columns(3)

# 基礎金額
food_base = edited_df[edited_df['Category'] == "Food 🍏"]['Price'].sum()
house_base = edited_df[edited_df['Category'] == "Household 🧻"]['Price'].sum()

# 折扣後金額
food_final = food_base * multiplier
house_final = house_base * multiplier

with col1:
    st.metric("Food 🍏", f"${food_final:.2f}", help=f"Original: ${food_base:.2f}")
with col2:
    st.metric("Household 🧻", f"${house_final:.2f}", help=f"Original: ${house_base:.2f}")
with col3:
    st.metric("Total (Discounted)", f"${(food_final + house_final):.2f}")

if discount_pct > 0:
    st.success(f"已套用 {discount_pct}% OFF 折扣")

# --- 7. 下載按鈕 ---
st.download_button("Export to CSV", edited_df.to_csv(index=False), "grocery_list.csv")