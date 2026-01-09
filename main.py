"""
SnowBot - 메인 앱
"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
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

def load_auth_config():
    try:
        with open('config_data/auth.yaml', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
            return config
    except FileNotFoundError:
        st.error("설정 파일(config_data/auth.yaml)을 찾을 수 없습니다.")
        return None

def main():
    """메인 함수"""
    
    config = load_auth_config()
    if config is None:
        return

    # [수정] 인증 사용 여부 확인 (설정이 없으면 기본값 True)
    auth_enabled = config.get('enabled', True)

    name = "snowbot" # 인증 미사용 시 표시할 기본 이름
    authenticator = None

    # --- 인증 로직 분기 ---
    if auth_enabled:
        # [CASE 1] 인증 적용 (로그인 창 표시)
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )

        # 로그인 위젯 표시 (최신 버전 대응: location 인자 사용, 반환값 없음)
        authenticator.login(location='main')

        # 세션 상태 확인
        if st.session_state["authentication_status"] is False:
            st.error('아이디 또는 비밀번호가 일치하지 않습니다.')
            return
        elif st.session_state["authentication_status"] is None:
            st.warning('아이디와 비밀번호를 입력해주세요.')
            return
        
        # 로그인 성공 시 이름 가져오기
        name = st.session_state["name"]

    else:
        # [CASE 2] 인증 미적용 (로그인 패스)
        # 앱 로직이 정상 동작하도록 세션 상태 강제 설정
        st.session_state["authentication_status"] = True
        st.session_state["name"] = name
        st.session_state["username"] = "admin"

    # --- 메인 앱 로직 (로그인 성공 또는 인증 패스 시 실행) ---
    
    # 사이드바 구성
    with st.sidebar:
        st.title("📈 SnowBot")
        st.write(f"환영합니다, **{name}**님! 👋")
        
        # 인증을 사용 중일 때만 로그아웃 버튼 표시
        if auth_enabled and authenticator:
            authenticator.logout(location='sidebar')
            
        st.markdown("---")
    
    # 스케줄러 가져오기
    scheduler = get_scheduler()

    # 메뉴 구성
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
    
    # 시스템 상태 표시 (기존 코드)
    from config.settings import get_settings_manager
    settings = get_settings_manager().settings
    
    # 계좌 모드 표시
    mode = settings.execution_mode
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
