"""
SnowBot - 메인 앱
"""

import streamlit as st
from scheduler.task_manager import get_scheduler

# 페이지 설정
st.set_page_config(
    page_title="SnowBot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-running {
        color: #28a745;
        font-weight: bold;
    }
    .status-stopped {
        color: #dc3545;
        font-weight: bold;
    }
    .account-simulation {
        background-color: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .account-mock {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .account-real {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

scheduler = get_scheduler()

def main():
    """메인 함수"""
    
    # 사이드바 메뉴
    st.sidebar.title("📈 SnowBot")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio(
        "메뉴",
        [
            "⚙️ 설정",
            "📥 데이터수집",
            "📊 종목평가",
            "🖐️ 수동매매",
            "⚡ 자동매매",
            "📈 대시보드"
        ],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # 시스템 상태 표시
    from config.settings import get_settings_manager
    settings = get_settings_manager().settings
    
    # 계좌 모드 표시
    mode = settings.execution_mode
    api_mode = settings.api.kis_api_mode
    api_account_mode = settings.api.kis_trading_account_mode
    
    if mode == "simulation":
        st.sidebar.success("🎮 시뮬레이션")
    elif api_account_mode == "mock":
        st.sidebar.warning("🧪 모의투자")
    else:
        st.sidebar.error("💰 실계좌")
    
    st.sidebar.caption(f"DB: {settings.database.db_type}")
    
    # 페이지 라우팅
    if menu == "⚙️ 설정":
        from ui.settings_page import render_settings
        render_settings()
    
    elif menu == "📥 데이터수집":
        from ui.data_collection_page import render_data_collection
        render_data_collection()
    
    elif menu == "📊 종목평가":
        from ui.evaluation_page import render_evaluation
        render_evaluation()
    
    elif menu == "🖐️ 수동매매":
        from ui.manual_trading_page import render_manual_trading
        render_manual_trading()
    
    elif menu == "⚡ 자동매매":
        from ui.auto_trading_page import render_auto_trading
        render_auto_trading()
    
    elif menu == "📈 대시보드":
        from ui.dashboard import render_dashboard
        render_dashboard()


if __name__ == "__main__":
    main()
