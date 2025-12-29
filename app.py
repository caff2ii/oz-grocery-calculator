import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 設置網頁標題與佈局
st.set_page_config(page_title="OZ Grocery Pro", layout="centered")

# --- 1. 連接 Google Sheets 與讀取記憶 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0) # 設定 ttl=0 確保每次都讀取最新數據
def load_memory():
    try:
        # 嘗試讀取，如果失敗(例如空的)就回傳空字典
        df = conn.read(worksheet="Sheet1")
        # 建立字典: {'MILK': 'Food 🍏', 'SHAMPOO': 'Household 🧻'}
        # 統一轉做大寫 (Upper) 方便對應
        if not df.empty and 'Item' in df.columns and 'Category' in df.columns:
            return pd.Series(df.Category.values, index=df.Item.str.upper()).to_dict()
        return {}
    except Exception:
        return {}

memory_dict = load_memory()

# 初始化 Session State (購物車)
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

st.title("🛒 澳洲超市極速計數機")

# --- 2. 輸入區域 (Form 設計：支援 Enter 提交) ---
st.caption("流程：輸入名 -> Tab -> 輸入價錢 -> Enter")

with st.form(key="entry_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 項目名稱
        input_item = st.text_input("項目名稱 (Item):", placeholder="e.g. Milk")
    
    with col2:
        # 金額
        input_price = st.number_input("金額 ($):", min_value=0.0, step=0.01, format="%.2f")

    # 分類選單 (預設 Food，提交後會自動修正)
    # 這裡不自動跳轉是為了讓 Form 的操作更順暢，我們在後台做 matching
    input_category = st.selectbox("分類 (預設 Food, 系統會自動根據舊紀錄修正):", 
                                  ["Food 🍏", "Household 🧻", "Other 📦"])

    # 提交按鈕 (Enter 鍵會觸發此按鈕)
    submitted = st.form_submit_button("➕ 加入清單 (Enter)", use_container_width=True)

    if submitted:
        if input_item and input_price > 0:
            # --- 智能分類邏輯 ---
            clean_name = input_item.strip()
            upper_name = clean_name.upper()
            
            final_category = input_category
            
            # 如果用戶保持預設 "Food"，但記憶中這東西是 "Household"，自動幫佢改
            # 除非用戶自己手動選了 "Other" 或其他，我們才尊重用戶選擇
            if input_category == "Food 🍏" and upper_name in memory_dict:
                final_category = memory_dict[upper_name]

            # 加入購物車
            st.session_state.shopping_cart.append({
                "Item": clean_name,
                "Price": input_price,
                "Category": final_category
            })
            st.rerun() # 立即刷新顯示清單
        elif not input_item:
            st.warning("請輸入項目名稱！")

# --- 3. 清單顯示與管理 ---
if st.session_state.shopping_cart:
    st.divider()
    st.subheader("📋 目前清單")
    
    # 顯示每一行 item
    for i, entry in enumerate(st.session_state.shopping_cart):
        c1, c2, c3 = st.columns([4, 2, 1])
        with c1:
            st.write(f"**{entry['Item']}**")
            st.caption(f"{entry['Category']}")
        with c2:
            st.write(f"${entry['Price']:.2f}")
        with c3:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.shopping_cart.pop(i)
                st.rerun()

    # --- 4. 計算與折扣 ---
    st.divider()
    st.subheader("💰 結算")
    
    # 折扣輸入
    discount_val = st.number_input("全單折扣 (例如 9折 輸入 10):", 0, 100, 0)
    multiplier = (100 - discount_val) / 100

    # 分類總計
    food_sum = sum(x['Price'] for x in st.session_state.shopping_cart if "Food" in x['Category']) * multiplier
    house_sum = sum(x['Price'] for x in st.session_state.shopping_cart if "Household" in x['Category']) * multiplier
    total_sum = food_sum + house_sum

    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Food 🍏 (折後)", f"${food_sum:.2f}")
    kpi2.metric("Household 🧻 (折後)", f"${house_sum:.2f}")
    
    st.success(f"### 總共要俾: ${total_sum:.2f}")

    # --- 5. 永久儲存按鈕 ---
    st.write("---")
    # 使用 primary type 讓按鈕變顯眼
    if st.button("💾 將新項目儲存到 Google Sheets", type="primary", use_container_width=True):
        with st.spinner("正在儲存記憶..."):
            try:
                # 1. 準備本次數據
                new_data = pd.DataFrame(st.session_state.shopping_cart)[['Item', 'Category']]
                
                # 2. 讀取舊數據 (忽略 Cache)
                old_data = conn.read(worksheet="Sheet1", ttl=0)
                
                # 3. 合併數據：保留舊的 + 新的，如果有重複名，保留最新的分類
                # 確保 Item 欄位是 String 類型以防錯誤
                if not old_data.empty:
                    old_data['Item'] = old_data['Item'].astype(str)
                
                combined_df = pd.concat([old_data, new_data])
                
                # 去除重複 (以 Item 名稱去重，保留最後一次輸入的分類)
                # str.upper() 確保大小寫不同都當同一個
                combined_df['Item_Upper'] = combined_df['Item'].str.upper()
                final_df = combined_df.drop_duplicates(subset=['Item_Upper'], keep='last')
                final_df = final_df.drop(columns=['Item_Upper']) # 移除輔助欄位
                
                # 4. 寫入 Google Sheets
                conn.update(worksheet="Sheet1", data=final_df)
                
                st.toast("✅ 成功儲存！下次輸入會自動記得分類。", icon="🎉")
                
                # 清空暫存，重新讀取記憶
                st.cache_data.clear()
                
            except Exception as e:
                st.error("儲存失敗！請檢查下方的「權限設定指南」。")
                st.expander("錯誤詳情 (Error Log)").write(e)

else:
    st.info("👆 請在上方輸入項目加入清單。")
