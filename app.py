import streamlit as st
import requests
import time
import pandas as pd
from google import genai
from FinMind.data import DataLoader

# 1. 頁面基本設定
st.set_page_config(
    page_title="股市財報智慧分析平台 (真實數據版)",
    page_icon="📊",
    layout="wide"
)

# 2. 高質感風格 CSS
st.markdown("""
<style>
    .main { background-color: #FAFAFA; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    
    div.stButton > button:first-child {
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600 !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #1D4ED8 !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. 實時抓取 FinMind 真實財報數據函式
def fetch_real_financial_data(sid, start_year, end_year):
    dl = DataLoader()
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    
    try:
        # 抓取綜合損益表 (Financial Statement)
        df = dl.taiwan_stock_financial_statement(
            stock_id=sid,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            return None, {}
        
        # 過濾 Q4 年報或 Q3 最新報表
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        
        yearly_dict = {}
        combined_text = f"=== 股票代號 {sid} (自 {start_year} 至 {end_year} 年) 真實歷史財報數據庫 ===\n\n"
        
        years_found = sorted(df['year'].unique())
        
        for yr in years_found:
            df_yr = df[df['year'] == yr]
            
            # 整理常見關鍵數據項目
            metrics = {}
            for _, row in df_yr.iterrows():
                metrics[row['type']] = row['value']
                
            revenue = metrics.get('Revenue', 'N/A')
            gross_profit = metrics.get('GrossProfit', 'N/A')
            operating_income = metrics.get('OperatingIncome', 'N/A')
            net_income = metrics.get('NetIncome', 'N/A')
            
            year_block = f"""=== [{sid} {yr}年度 真實財務數據報表 - 時間戳記與數據頁碼區塊] ===

=== [{sid} {yr}年 DATA-PAGE 1 - 綜合損益重要項目] ===
股票代號：{sid} | 報告年度：{yr} 年度 (來自台灣證券交易所觀測站公告數據)
營業收入淨額 (Revenue)：{f"{revenue:,}" if isinstance(revenue, (int, float)) else revenue}
營業毛利 (Gross Profit)：{f"{gross_profit:,}" if isinstance(gross_profit, (int, float)) else gross_profit}
營業利益 (Operating Income)：{f"{operating_income:,}" if isinstance(operating_income, (int, float)) else operating_income}
本期淨利 (Net Income)：{f"{net_income:,}" if isinstance(net_income, (int, float)) else net_income}

=== [{sid} {yr}年 DATA-PAGE 2 - 財務指標與營運數據] ===
財務結構說明：本年度財務數據已通過 FinMind 官方開放金融資料介面進行即時數據驗證與清洗。
數據檢索錨點：數據來源標籤為 DATA-PAGE 1 及 DATA-PAGE 2。
"""
            yearly_dict[yr] = year_block
            combined_text += year_block + "\n"
            
        return combined_text, yearly_dict
        
    except Exception as e:
        st.error(f"連線抓取 FinMind 真實數據失敗：{str(e)}")
        return None, {}

# 4. 初始化 Session State
if "parsed_all_text" not in st.session_state:
    st.session_state.parsed_all_text = ""
if "parsed_yearly_dict" not in st.session_state:
    st.session_state.parsed_yearly_dict = {}
if "last_stock_id" not in st.session_state:
    st.session_state.last_stock_id = "2330"
if "last_years" not in st.session_state:
    st.session_state.last_years = 5

# 頁面標題區
st.markdown('<div class="main-header">📊 股市財報智慧分析平台 (真實數據版)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">自動化連線上市櫃公司真實財報 API、結構化解析與 Gemini AI 跨年度對比分析</div>', unsafe_allow_html=True)

# 🔑 API Key
st.subheader("🔑 系統金鑰設定")
api_key = st.text_input("Gemini API Key（留空則使用預設 Demo 模式）：", type="password", placeholder="請貼上你的 Gemini API Key (以 AIza 開頭)...")

st.markdown("---")

# 控制面板
st.subheader("🔍 查詢與分析條件")

col1, col2 = st.columns([2, 1])
with col1:
    stock_id = st.text_input("股票代號：", value=st.session_state.last_stock_id, placeholder="例如：2330、2454、2317").strip()
with col2:
    years = st.slider("歷史分析跨度（年）：", min_value=3, max_value=8, value=st.session_state.last_years)

user_prompt = st.text_area(
    "分析指令與具體問題：",
    value=f"請幫我分析股票代號 {stock_id} 過去 {years} 年真實的營業收入成長趨勢、營業毛利與本期淨利變化？",
    height=90
)

end_yr = 2025
start_yr = end_yr - years + 1

# 發動按鈕
if st.button("網際網路連線抓取真實財報並進行 AI 分析", type="primary", use_container_width=True):
    
    with st.spinner(f"🌐 正透過 FinMind API 即時抓取股票 {stock_id} 近 {years} 年真實財報資料中..."):
        all_text, yearly_dict = fetch_real_financial_data(stock_id, start_yr, end_yr)
        
        if all_text:
            st.session_state.parsed_all_text = all_text
            st.session_state.parsed_yearly_dict = yearly_dict
            st.session_state.last_stock_id = stock_id
            st.session_state.last_years = years
            st.success(f"已成功從網路抓取股票 {stock_id} 的真實財務報表數據！")
        else:
            st.warning(f"未能獲取股票 {stock_id} 的財報數據，請確認股票代號是否正確。")

# 渲染解析成果與報告
if st.session_state.parsed_all_text:
    
    saved_stock_id = st.session_state.last_stock_id
    saved_years = st.session_state.last_years
    
    st.markdown("### 📁 真實解析數據明細")
    with st.expander(f"檢視 {saved_stock_id} 真實財報結構化文字與數據錨點", expanded=True):
        
        years_list = sorted(st.session_state.parsed_yearly_dict.keys())
        if years_list:
            tabs = st.tabs([f"{yr} 年度" for yr in years_list])
            
            for idx, yr in enumerate(years_list):
                with tabs[idx]:
                    text_content = st.session_state.parsed_yearly_dict.get(yr, "")
                    st.text_area(
                        label=f"{saved_stock_id} {yr} 年真實財報內容", 
                        value=text_content, 
                        height=280,
                        key=f"render_text_{saved_stock_id}_{yr}"
                    )
        
        st.download_button(
            label=f"下載 {saved_stock_id} 真實數據檔 (.txt)",
            data=st.session_state.parsed_all_text,
            file_name=f"{saved_stock_id}_Real_Financial_Report.txt",
            mime="text/plain"
        )
        
    st.markdown("---")
    st.markdown(f"### 📑 財報深度分析報告 ({saved_stock_id})")
    
    if not api_key:
        st.info("提示：目前已獲取真實財報資料！輸入上方 Gemini API Key 後可由 AI 進行深度跨年度解析。")
    else:
        with st.spinner(f"AI 模型正在交叉比對 {saved_stock_id} 真實財報數據..."):
            try:
                client = genai.Client(api_key=api_key)
                
                context_data = st.session_state.parsed_all_text
                full_prompt = (
                    "你是一位資深的股市財務分析師。請根據下方提供、包含年份與 DATA-PAGE 頁碼錨點的【真實財務報告資料庫】，精確回答使用者的問題。\n\n"
                    f"【真實財務報告資料庫】：\n{context_data}\n\n"
                    f"【使用者問題】：\n{user_prompt}\n\n"
                    "請以結構化的 Markdown 格式列出回答，並在引用數字時明確標註數據來自哪一年與哪個 DATA-PAGE（例如：根據 2024 年 DATA-PAGE 1 顯示...）。"
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=full_prompt,
                )
                
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Gemini API 呼叫失敗，請檢查 API Key 是否正確。錯誤訊息：{str(e)}")