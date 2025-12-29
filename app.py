import streamlit as st
import pandas as pd
import json
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="OZ Grocery Pro v1.9", layout="centered")

# --- 1. 讀取數據 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def get_data_json():
    try:
        df = conn.read(worksheet="Sheet1")
        if not df.empty:
            # 準備畀 JS 用嘅資料格式：[{"item": "Milk", "cat": "Food 🍏"}, ...]
            data = []
            for _, row in df.iterrows():
                data.append({"item": str(row['Item']).title(), "cat": str(row['Category'])})
            return json.dumps(data)
        return "[]"
    except:
        return "[]"

history_json = get_data_json()

# --- 2. Session State ---
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

# --- 3. JS 注入 (核心黑科技) ---
# 呢段代碼會喺前端畫一個隱藏嘅「數據池」，並監控輸入框
st.markdown(f"""
    <div id="js-logic">
        <script>
            // 獲取 Python 傳過嚟嘅歷史紀錄
            const history = {history_json};
            
            // 定時檢查輸入框是否存在 (因為 Streamlit 會重新渲染)
            const interval = setInterval(() => {{
                const input = window.parent.document.querySelector('input[aria-label="1. 項目名稱 (JS 即時聯想)"]');
                if (input && !input.dataset.listener) {{
                    input.dataset.listener = "true";
                    input.setAttribute('autocomplete', 'off'); // 停用瀏覽器紀錄
                    
                    // 建立建議列表容器
                    const list = window.parent.document.createElement('div');
                    list.id = "sug-list";
                    list.style = "position:absolute; background:white; width:100%; z-index:1000; border:1px solid #ddd; border-top:none; display:none; color: black;";
                    input.parentNode.appendChild(list);

                    input.addEventListener('input', (e) => {{
                        const val = e.target.value.toUpperCase();
                        list.innerHTML = '';
                        if (!val) {{ list.style.display = 'none'; return; }}
                        
                        const matches = history.filter(h => h.item.toUpperCase().includes(val)).slice(0, 5);
                        if (matches.length > 0) {{
                            list.style.display = 'block';
                            matches.forEach(m => {{
                                const item = window.parent.document.createElement('div');
                                item.innerHTML = `<b>${{m.item}}</b> <small>(${{m.cat}})</small>`;
                                item.style = "padding:10px; cursor:pointer; border-bottom:1px solid #eee;";
                                item.onclick = () => {{
                                    input.value = m.item;
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    list.style.display = 'none';
                                    
                                    // 自動填寫分類 (Streamlit 嘅 selectbox 比較難直接改，我哋靠 Python 判定)
                                }};
                                list.appendChild(item);
                            }});
                        }} else {{
                            list.style.display = 'none';
                        }}
                    }});
                }}
            }}, 500);
        </script>
    </div>
""", unsafe_allow_html=True)

# --- 4. 介面 (UI) ---
st.title("🛒 超市助手 v1.9 (JS Engine)")

name_val = st.text_input("1. 項目名稱 (JS 即時聯想)", key="name_input")

col_p, col_c = st.columns(2)
with col_c:
    # 呢度仲係用 Python 做分類預測
    current_name = name_val.upper()
    # 喺 history_json 搵返分類
    history_list = json.loads(history_json)
    found_cat = next((h['cat'] for h in history_list if h['item'].upper() == current_name), "Food 🍏")
    
    cat_options = ["Food 🍏", "Household 🧻", "Other 📦"]
    selected_cat = st.selectbox("2. 分類:", options=cat_options, index=cat_options.index(found_cat) if found_cat in cat_options else 0, key="cat_input")

with col_p:
    price = st.number_input("3. 金額 ($):", min_value=0.0, format="%.2f", key="price_input", step=0.01)

if st.button("➕ 加入清單", use_container_width=True, type="primary"):
    if name_val and price > 0:
        st.session_state.shopping_cart.append({
            "Item": name_val.title(),
            "Price": price,
            "Category": selected_cat
        })
        st.rerun()

# --- 5. 清單顯示 ---
if st.session_state.shopping_cart:
    st.divider()
    df_cart = pd.DataFrame(st.session_state.shopping_cart)
    st.table(df_cart)
    
    total = df_cart['Price'].sum()
    st.success(f"### 總額: ${total:.2f}")

    if st.button("💾 儲存並更新記憶庫", use_container_width=True):
        old_df = conn.read(worksheet="Sheet1")
        updated_df = pd.concat([old_df, df_cart[['Item', 'Category']]]).drop_duplicates(subset=['Item'], keep='last')
        conn.update(worksheet="Sheet1", data=updated_df)
        st.toast("✅ 儲存成功！")
        st.cache_data.clear()
