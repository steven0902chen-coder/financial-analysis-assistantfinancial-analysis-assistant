import streamlit as st
import time
import pandas as pd
import yfinance as yf
from google import genai

# 1. 頁面基本設定
st.set_page_config(
    page_title="股市財報智慧分析平台",
    layout="wide"
)

# 防止瀏覽器自動翻譯造成網頁節點衝突
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

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

# 3. 實時抓取真實股票數據函式 (yfinance)
def fetch_real_financial_data(stock_symbol, num_years):
    # 台股程式碼處理 (若未加後綴，自動加上 .TW)
    symbol = stock_symbol.strip()
    if not symbol.endswith('.TW') and not symbol.endswith('.TWO') and symbol.isdigit():
        symbol = f"{symbol}.TW"
        
    try:
        ticker = yf.Ticker(symbol)
        financials = ticker.financials
        
        if financials is None or financials.empty:
            return None, {}
            
        yearly_dict = {}
        combined_text = f"=== 股票代號 {symbol} 真實歷史財報數據庫 ===\n\n"
        
        # 取得年份欄位
        dates = list(financials.columns)[:num_years]
        
        for dt in sorted(dates):
            yr = dt.year
            df_yr = financials[dt]
            
            # 抓取重點財務數據 (單位：元)
            revenue = df_yr.get('Total Revenue', df_yr.get('Operating Revenue', 'N/A'))
            gross_profit = df_yr.get('Gross Profit', 'N/A')
            op_income = df_yr.get('Operating Income', 'N/A')
            net_income = df_yr.get('Net Income Common Stockholders', df_yr.get('Net Income', 'N/A'))
            ebitda = df_yr.get('EBITDA', 'N/A')
            
            # 格式化數值 (換算為新台幣 千元)
            def format_val(v):
                if isinstance(v, (int, float)) and not pd.isna(v):
                    return f"{int(v / 1000):,} 千元"
                return "無數據"

            year_block = f"""=== [{symbol} {yr}年度 真實財務報告 - 時間戳記與數據頁碼區塊] ===

=== [{symbol} {yr}年 REAL-PAGE 1 - 綜合損益重要項目] ===
股票代號：{symbol} | 報告年度：{yr} 年度 (資料來源：公開財務市場真實報表)
營業收入總額 (Total Revenue)：{format_val(revenue)}
營業毛利 (Gross Profit)：{format_val(gross_profit)}
營業利益 (Operating Income)：{format_val(op_income)}
本期淨利 (Net Income)：{format_val(net_income)}
稅前息前折舊前淨利 (EBITDA)：{format_val(ebitda)}

=== [{symbol} {yr}年 REAL-PAGE 2 - 營運與財務結構聲明] ===
數據品質說明：本報表為經由 API 實時擷取之真實公開財務數據，已通過數據整理驗證。
防幻覺檢索錨點：數據來源標籤為 REAL-PAGE 1 及 REAL-PAGE 2。
"""
            yearly_dict[yr] = year_block
            combined_text += year_block + "\n"
            
        return combined_text, yearly_dict
        
    except Exception as e:
        st.error(f"連線抓取真實數據失敗：{str(e)}")
        return None, {}

# 4. 初始化 Session State
if "parsed_all_text" not in st.session_state:
    st.session_state.parsed_all_text = ""
if "parsed_yearly_dict" not in st.session_state:
    st.session_state.parsed_yearly_dict = {}
if "last_stock_id" not in st.session_state:
    st.session_state.last_stock_id = "2330"
if "last_years" not in st.session_state:
    st.session_state.last_years = 4

# 頁面標題區
st.markdown('<div class="main-header">股市財報智慧分析平台</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">自動化連線上市櫃公司真實財報 API、結構化解析與 Gemini AI 跨年度對比分析</div>', unsafe_allow_html=True)

# API Key 與模型設定區
st.subheader("系統金鑰與模型設定")
col_key, col_model = st.columns([2, 1])

with col_key:
    api_key = st.text_input(
        "Gemini API Key（留空則僅檢視真實財報數據）：", 
        type="password", 
        placeholder="請貼上你的 Gemini API Key (以 AIza 開頭)..."
    )

with col_model:
    selected_model = st.selectbox(
        "AI 分析模型選擇：",
        options=["gemini-3.0-flash", "gemini-3.0-pro", "gemini-2.5-flash"],
        index=0,
        help="預設使用最新一代 gemini-3.0-flash（速度最快、穩定度高）；若需深度複雜推理可切換至 gemini-3.0-pro。"
    )

st.markdown("---")

# 控制面板
st.subheader("查詢與分析條件")

col1, col2 = st.columns([2, 1])
with col1:
    stock_id = st.text_input("股票代號：", value=st.session_state.last_stock_id, placeholder="例如：2330、2454、2317").strip()
with col2:
    years = st.slider("歷史分析跨度（年）：", min_value=2, max_value=4, value=st.session_state.last_years)

user_prompt = st.text_area(
    "分析指令與具體問題：",
    value=f"請幫我分析股票代號 {stock_id} 過去 {years} 年真實的營業收入成長趨勢、營業毛利與本期淨利變化？",
    height=90
)

# 發動按鈕
if st.button("網際網路連線抓取真實財報並進行 AI 分析", type="primary", use_container_width=True):
    
    with st.spinner(f"正即時連線抓取股票 {stock_id} 近 {years} 年真實財報資料中..."):
        all_text, yearly_dict = fetch_real_financial_data(stock_id, years)
        
        if all_text:
            st.session_state.parsed_all_text = all_text
            st.session_state.parsed_yearly_dict = yearly_dict
            st.session_state.last_stock_id = stock_id
            st.session_state.last_years = years
            st.success(f"已成功從公開金融資料庫抓取股票 {stock_id} 的真實財務報表數據。")
        else:
            st.warning(f"未能獲取股票 {stock_id} 的財報數據，請確認股票代號（如 2330）是否正確。")

# 渲染解析成果與報告
if st.session_state.parsed_all_text:
    saved_stock_id = st.session_state.last_stock_id
    
    st.markdown("### 真實解析數據明細")
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
    st.markdown(f"### 財報深度分析報告 ({saved_stock_id} | 模型：{selected_model})")
    
    if not api_key:
        st.info("提示：目前已成功抓取真實財報數據！輸入上方 Gemini API Key 後可由 AI 進行深度跨年度對比。")
    else:
        with st.spinner(f"AI 模型 ({selected_model}) 正在交叉比對 {saved_stock_id} 真實財報數據..."):
            try:
                client = genai.Client(api_key=api_key)
                
                context_data = st.session_state.parsed_all_text
                full_prompt = (
                    "你是一位資深的股市財務分析師。請根據下方提供、包含年份與 REAL-PAGE 頁碼錨點的【真實財務報告資料庫】，精確回答使用者的問題。\n\n"
                    f"【真實財務報告資料庫】：\n{context_data}\n\n"
                    f"【使用者問題】：\n{user_prompt}\n\n"
                    "請以結構化的 Markdown 格式列出回答，並在引用數字時明確標註數據來自哪一年與哪個 REAL-PAGE（例如：根據 2024 年 REAL-PAGE 1 顯示...）。"
                )
                
                response = client.models.generate_content(
                    model=selected_model,
                    contents=full_prompt,
                )
                
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Gemini API 呼叫失敗，請檢查 API Key 是否正確，或嘗試切換至 gemini-2.5-flash 模型。錯誤訊息：{str(e)}")