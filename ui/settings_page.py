"""
설정 페이지
- API 키 설정 (첫번째 탭)
- 계좌 설정 (시뮬레이션/실거래)
- 데이터베이스 설정
- 매매 설정
- 스케줄 관리 (schedule_page.py 연동)
"""

import streamlit as st
from datetime import datetime
import uuid

from config.settings import get_settings_manager, ScheduleItem
from config.database import get_session, VirtualAccount

# [수정 1] 스케줄 관리 페이지 모듈 임포트
from ui.schedule_page import render_schedule


def render_settings():
    """설정 페이지 렌더링"""
    st.markdown('<div class="main-header">⚙️ 설정</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    settings = settings_manager.settings
    
    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔑 API 키",
        "💳 계좌 설정",
        "🗄️ 데이터베이스",
        "💹 매매 설정",
        "📅 스케줄 관리"
    ])
    
    # ========== API 키 설정 (첫번째 탭) ==========
    with tab1:
        render_api_settings(settings_manager, settings)
    
    # ========== 계좌 설정 (두번째 탭) ==========
    with tab2:
        render_account_settings(settings_manager, settings)
    
    # ========== 데이터베이스 설정 ==========
    with tab3:
        render_database_settings(settings_manager, settings)
    
    # ========== 매매 설정 ==========
    with tab4:
        render_trading_settings(settings_manager, settings)
    
    # ========== 스케줄 관리 ==========
    with tab5:
        # [수정 2] 기존 내부 함수 대신 외부 모듈의 함수 호출
        # render_schedule_management()  <-- 삭제/주석 처리
        render_schedule()  # <-- ui/schedule_page.py의 함수 사용


def render_api_settings(settings_manager, settings):
    """API 키 설정 탭 (계좌번호 제외, API 정보만)"""
    st.subheader("API 키 설정")
    
    st.info("💡 데이터 수집 및 매매에 필요한 API 키를 설정합니다. 계좌 번호는 '계좌 설정' 탭에서 설정하세요.")
    
    # ========== KRX API ==========
    st.markdown("#### 📈 KRX API")
    krx_api_key = st.text_input(
        "KRX API 키",
        value=settings.api.krx_api_key,
        type="password",
        help="KRX 데이터 포털에서 발급받은 API 키"
    )
    st.caption("💡 [KRX 데이터 포털](https://data.krx.co.kr/)에서 발급받을 수 있습니다.")
    
    st.divider()
    
    # ========== OpenDart API ==========
    st.markdown("#### 📊 OpenDart API")
    opendart_key = st.text_input(
        "OpenDart API 키",
        value=settings.api.opendart_api_key,
        type="password",
        help="OpenDart에서 발급받은 API 키 (재무제표 조회용)"
    )
    st.caption("💡 [OpenDart](https://opendart.fss.or.kr/)에서 무료로 발급받을 수 있습니다.")
    
    st.divider()
    
    # ========== KIS API ==========
    st.markdown("#### 🏦 KIS(한국투자증권) API")
    st.caption("💡 [KIS Developers](https://apiportal.koreainvestment.com/)에서 발급받을 수 있습니다.")
    
    # 모의투자 API 정보
    st.markdown("##### 🧪 모의투자 API")
    col1, col2 = st.columns(2)
    
    with col1:
        kis_mock_app_key = st.text_input(
            "App Key (모의)",
            value=settings.api.kis_mock_app_key,
            type="password",
            key="mock_app_key"
        )
    
    with col2:
        kis_mock_app_secret = st.text_input(
            "App Secret (모의)",
            value=settings.api.kis_mock_app_secret,
            type="password",
            key="mock_app_secret"
        )
    
    st.divider()
    
    # 실전투자 API 정보
    st.markdown("##### 💰 실전투자 API")
    col1, col2 = st.columns(2)
    
    with col1:
        kis_real_app_key = st.text_input(
            "App Key (실전)",
            value=settings.api.kis_real_app_key,
            type="password",
            key="real_app_key"
        )
    
    with col2:
        kis_real_app_secret = st.text_input(
            "App Secret (실전)",
            value=settings.api.kis_real_app_secret,
            type="password",
            key="real_app_secret"
        )
    
    st.divider()
    
    # ========== 데이터 수집용 API 선택 ==========
    st.markdown("#### 📡 데이터 수집 API 선택")
    st.info("💡 시세, PER/PBR, 수급 등 데이터 수집에 사용할 KIS API를 선택합니다. (거래 계좌와 별도)")
    
    # API 설정 상태 표시
    has_mock_api = bool(kis_mock_app_key and kis_mock_app_secret)
    has_real_api = bool(kis_real_app_key and kis_real_app_secret)
    
    col1, col2 = st.columns(2)
    with col1:
        if has_mock_api:
            st.success("✅ 모의투자 API 설정됨")
        else:
            st.warning("⚠️ 모의투자 API 미설정")
    with col2:
        if has_real_api:
            st.success("✅ 실전투자 API 설정됨")
        else:
            st.warning("⚠️ 실전투자 API 미설정")
    
    # 토큰 상태 표시
    st.markdown("##### 🔐 토큰 상태")
    try:
        from data.price_fetcher import get_token_manager
        token_manager = get_token_manager()
        
        col1, col2 = st.columns(2)
        with col1:
            mock_status = token_manager.get_token_status('mock')
            if mock_status['is_valid']:
                remaining = mock_status['remaining_time']
                hours = remaining.seconds // 3600
                mins = (remaining.seconds % 3600) // 60
                st.info(f"🧪 모의: 토큰 유효 ({hours}시간 {mins}분 남음)\n발급 {mock_status['issue_count_today']}/5회")
            else:
                st.caption(f"🧪 모의: 토큰 없음 (발급 {mock_status['issue_count_today']}/5회)")
        
        with col2:
            real_status = token_manager.get_token_status('real')
            if real_status['is_valid']:
                remaining = real_status['remaining_time']
                hours = remaining.seconds // 3600
                mins = (remaining.seconds % 3600) // 60
                st.info(f"💰 실전: 토큰 유효 ({hours}시간 {mins}분 남음)\n발급 {real_status['issue_count_today']}/5회")
            else:
                st.caption(f"💰 실전: 토큰 없음 (발급 {real_status['issue_count_today']}/5회)")
    except Exception as e:
        st.caption(f"토큰 상태 조회 불가: {e}")
    
    current_api_mode = settings.api.kis_api_mode
    
    kis_api_mode = st.radio(
        "데이터 수집에 사용할 API",
        options=["mock", "real"],
        format_func=lambda x: "🧪 모의투자 API" if x == "mock" else "💰 실전투자 API",
        index=0 if current_api_mode == "mock" else 1,
        horizontal=True,
        key="api_mode_select"
    )
    
    if kis_api_mode == "real" and not has_real_api:
        st.error("❌ 실전투자 API가 설정되지 않았습니다. 위에서 App Key와 App Secret을 입력하세요.")
    elif kis_api_mode == "mock" and not has_mock_api:
        st.error("❌ 모의투자 API가 설정되지 않았습니다. 위에서 App Key와 App Secret을 입력하세요.")
    
    st.divider()
    
    # 저장 버튼
    if st.button("💾 API 설정 저장", key="save_api", type="primary"):
        settings_manager.update_api(
            opendart_api_key=opendart_key,
            krx_api_key=krx_api_key,
            kis_mock_app_key=kis_mock_app_key,
            kis_mock_app_secret=kis_mock_app_secret,
            kis_real_app_key=kis_real_app_key,
            kis_real_app_secret=kis_real_app_secret,
            kis_api_mode=kis_api_mode
        )
        st.success("✅ API 설정이 저장되었습니다.")


def render_account_settings(settings_manager, settings):
    """계좌 설정 탭"""
    st.subheader("계좌 설정")
    
    # ========== 실행 모드 선택 ==========
    st.markdown("#### 실행 모드")
    
    st.info("""
    **실행 모드 안내:**
    - **시뮬레이션**: 시스템 내부 가상 계좌로 매매를 테스트합니다. 실제 거래 없이 전략을 검증할 수 있습니다.
    - **실거래**: 증권사 API를 통해 실제 매매를 수행합니다.
    """)
    
    current_mode = settings.execution_mode
    
    mode_options = {
        "simulation": "🎮 시뮬레이션 (시스템 내부 가상 계좌)",
        "real_trading": "💰 실거래 (증권사 API 연동)"
    }
    
    selected_mode = st.radio(
        "실행 모드 선택",
        options=list(mode_options.keys()),
        format_func=lambda x: mode_options[x],
        index=0 if current_mode == "simulation" else 1,
        key="exec_mode_radio"
    )
    
    st.divider()
    
    # ========== 모드별 설정 ==========
    if selected_mode == "simulation":
        render_simulation_settings(settings_manager, settings)
    else:
        render_real_trading_settings(settings_manager, settings)


def render_simulation_settings(settings_manager, settings):
    """시뮬레이션 모드 설정"""
    st.markdown("### 🎮 시뮬레이션 설정")
    
    st.success("✅ 시뮬레이션 모드: 가상 자금으로 안전하게 테스트합니다.")
    
    # 가상 계좌 정보 조회
    virtual_account = get_virtual_account()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 💰 가상 계좌 설정")
        
        # 총 자금 설정
        initial_balance = st.number_input(
            "초기 투자금 (원)",
            min_value=1_000_000,
            max_value=10_000_000_000,
            value=virtual_account.get('balance', 100_000_000) if virtual_account else 100_000_000,
            step=10_000_000,
            format="%d"
        )
        st.caption(f"💵 설정 금액: {initial_balance:,.0f}원")
    
    with col2:
        st.markdown("##### 📊 현재 가상 계좌 현황")
        if virtual_account:
            st.metric("예수금", f"{virtual_account.get('balance', 0):,.0f}원")
            st.metric("총 평가금액", f"{virtual_account.get('total_eval', 0):,.0f}원")
            st.metric("총 손익", f"{virtual_account.get('total_profit', 0):,.0f}원")
        else:
            st.info("가상 계좌가 초기화되지 않았습니다.")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 설정 저장", type="primary", key="save_sim"):
            settings_manager.update(execution_mode="simulation")
            update_virtual_account(initial_balance)
            st.success("✅ 시뮬레이션 설정이 저장되었습니다.")
            st.rerun()
    
    with col2:
        if st.button("🔄 계좌 초기화", key="reset_sim"):
            st.session_state.show_reset_confirm = True
    
    # 초기화 확인
    if st.session_state.get('show_reset_confirm', False):
        st.warning("⚠️ 가상 계좌를 초기화하시겠습니까? 모든 보유 종목과 거래 내역이 삭제됩니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 확인", key="confirm_reset"):
                reset_virtual_account(initial_balance)
                st.session_state.show_reset_confirm = False
                st.success("✅ 가상 계좌가 초기화되었습니다.")
                st.rerun()
        with col2:
            if st.button("❌ 취소", key="cancel_reset"):
                st.session_state.show_reset_confirm = False
                st.rerun()


def render_real_trading_settings(settings_manager, settings):
    """실거래 모드 설정"""
    st.markdown("### 💰 실거래 설정")
    
    # API 키 설정 여부 확인
    has_mock_api = bool(settings.api.kis_mock_app_key and settings.api.kis_mock_app_secret)
    has_real_api = bool(settings.api.kis_real_app_key and settings.api.kis_real_app_secret)
    
    if not has_mock_api and not has_real_api:
        st.error("❌ 증권사 API가 설정되지 않았습니다. 'API 키' 탭에서 먼저 API 정보를 설정해주세요.")
        return
    
    st.info("""
    💡 **거래 계좌 안내**
    - 거래에 사용할 계좌를 선택합니다.
    - 데이터 수집용 API는 'API 키' 탭에서 별도로 설정됩니다.
    - 예: 실전투자 API로 데이터를 수집하고, 모의계좌로 거래 테스트 가능
    """)
    
    # API 상태 표시
    st.markdown("#### 📡 API 설정 상태")
    col1, col2 = st.columns(2)
    with col1:
        if has_mock_api:
            st.success("✅ 모의투자 API 설정됨")
        else:
            st.warning("⚠️ 모의투자 API 미설정")
    with col2:
        if has_real_api:
            st.success("✅ 실전투자 API 설정됨")
        else:
            st.warning("⚠️ 실전투자 API 미설정")
    
    # 현재 데이터 수집 API 표시
    current_data_api = settings.api.kis_api_mode
    st.caption(f"📊 데이터 수집 API: {'실전투자' if current_data_api == 'real' else '모의투자'} (API 키 탭에서 변경)")
    
    st.divider()
    
    # 거래 계좌 선택
    st.markdown("#### 📋 거래 계좌 선택")
    
    # 현재 거래 계좌 모드 (kis_trading_account_mode 사용, 없으면 mock 기본)
    current_trading_mode = getattr(settings.api, 'kis_trading_account_mode', 'mock')
    
    account_mode = st.radio(
        "거래에 사용할 계좌",
        options=["mock", "real"],
        format_func=lambda x: "🧪 모의계좌 (모의투자)" if x == "mock" else "💳 실계좌 (실전투자)",
        index=0 if current_trading_mode == "mock" else 1,
        horizontal=True,
        key="account_mode_radio"
    )
    
    st.divider()
    
    # 계좌 번호 설정
    if account_mode == "mock":
        st.markdown("##### 🧪 모의계좌 설정")
        
        if not has_mock_api:
            st.error("❌ 모의투자 API가 설정되지 않았습니다. 'API 키' 탭에서 먼저 설정해주세요.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            mock_account_no = st.text_input(
                "모의계좌 번호 (8자리)",
                value=settings.api.kis_mock_account_no,
                max_chars=8,
                key="mock_acct_no"
            )
        
        with col2:
            mock_account_cd = st.text_input(
                "계좌상품코드 (2자리)",
                value=settings.api.kis_mock_account_cd,
                max_chars=2,
                key="mock_acct_cd"
            )
        
        st.info("💡 모의투자 계좌로 실제 자금 없이 거래를 테스트할 수 있습니다.")
        
        if st.button("💾 모의계좌 설정 저장", type="primary", key="save_mock"):
            settings_manager.update(execution_mode="real_trading")
            settings_manager.update_api(
                kis_trading_account_mode="mock",
                kis_mock_account_no=mock_account_no,
                kis_mock_account_cd=mock_account_cd
            )
            st.success("✅ 모의계좌 설정이 저장되었습니다.")
    
    else:  # real
        st.markdown("##### 💳 실계좌 설정")
        
        # 실전투자 API 체크
        if not has_real_api:
            st.error("""
            ❌ **실전투자 API가 설정되지 않았습니다.**
            
            실계좌로 거래하려면 실전투자 API가 필요합니다.
            'API 키' 탭에서 실전투자 App Key와 App Secret을 먼저 설정해주세요.
            """)
            
            if st.button("🔑 API 키 탭으로 이동", key="go_to_api"):
                st.info("👆 상단의 'API 키' 탭을 클릭하세요.")
            return
        
        # 위험 경고
        st.error("""
        🚨 **실계좌 사용 주의사항**
        
        실계좌를 선택하면 **실제 자금**으로 거래가 실행됩니다.
        자동매매 프로그램 사용으로 인한 투자 손실에 대해 본인이 전적으로 책임집니다.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            real_account_no = st.text_input(
                "실계좌 번호 (8자리)",
                value=settings.api.kis_real_account_no,
                max_chars=8,
                key="real_acct_no"
            )
        
        with col2:
            real_account_cd = st.text_input(
                "계좌상품코드 (2자리)",
                value=settings.api.kis_real_account_cd,
                max_chars=2,
                key="real_acct_cd"
            )
        
        st.divider()
        
        # 동의 체크박스
        agree_risk = st.checkbox(
            "⚠️ 위 주의사항을 모두 읽었으며, 실계좌 사용으로 인한 투자 손실에 대해 본인이 책임집니다.",
            key="agree_risk_checkbox"
        )
        
        if st.button("💾 실계좌 설정 저장", type="primary", disabled=not agree_risk, key="save_real"):
            settings_manager.update(execution_mode="real_trading")
            settings_manager.update_api(
                kis_trading_account_mode="real",
                kis_real_account_no=real_account_no,
                kis_real_account_cd=real_account_cd,
                kis_real_confirmed=True
            )
            st.success("✅ 실계좌 설정이 저장되었습니다.")
            st.warning("⚠️ 실계좌가 적용되었습니다. 모든 거래가 실제 자금으로 실행됩니다!")


def get_virtual_account():
    """가상 계좌 정보 조회"""
    try:
        with get_session() as session:
            account = session.query(VirtualAccount).first()
            if account:
                return {
                    'balance': account.balance or 0,
                    'total_eval': account.total_eval or 0,
                    'total_profit': account.total_profit or 0,
                    'total_profit_rate': account.total_profit_rate or 0.0
                }
            return None
    except:
        return None


def update_virtual_account(balance: int):
    """가상 계좌 업데이트"""
    try:
        with get_session() as session:
            account = session.query(VirtualAccount).first()
            if account:
                account.balance = balance
                account.total_eval = balance
            else:
                new_account = VirtualAccount(
                    balance=balance,
                    total_eval=balance,
                    total_profit=0,
                    total_profit_rate=0.0
                )
                session.add(new_account)
    except Exception as e:
        st.error(f"계좌 업데이트 오류: {e}")


def reset_virtual_account(balance: int):
    """가상 계좌 초기화"""
    try:
        from config.database import VirtualHolding, TradeHistory
        
        with get_session() as session:
            # 보유 종목 삭제
            session.query(VirtualHolding).delete()
            
            # 가상 계좌 초기화
            session.query(VirtualAccount).delete()
            
            new_account = VirtualAccount(
                balance=balance,
                total_eval=balance,
                total_profit=0,
                total_profit_rate=0.0
            )
            session.add(new_account)
    except Exception as e:
        st.error(f"계좌 초기화 오류: {e}")


def render_database_settings(settings_manager, settings):
    """데이터베이스 설정 탭"""
    st.subheader("데이터베이스 설정")
    
    st.markdown("#### 데이터베이스 연결")
    
    db_type = st.selectbox(
        "DB 유형",
        options=["sqlite", "oracle"],
        format_func=lambda x: "SQLite (로컬)" if x == "sqlite" else "Oracle (ATP)",
        index=0 if settings.database.db_type == "sqlite" else 1
    )
    
    if db_type == "sqlite":
        st.info("📁 로컬 SQLite 데이터베이스를 사용합니다.")
        
        db_path = st.text_input(
            "DB 파일 경로",
            value=settings.database.sqlite_path,
            help="SQLite 데이터베이스 파일 경로"
        )
        
        if st.button("💾 데이터베이스 설정 저장", key="save_db"):
            settings_manager.update_database(
                db_type="sqlite",
                sqlite_path=db_path
            )
            st.success("✅ 데이터베이스 설정이 저장되었습니다.")
    
    else:
        st.markdown("#### Oracle ATP 설정 (Cloud)")
        st.info("경로 표현시 **백슬래시(\\\\)가 특수 문자로 인식**되므로, 반드시 두 번(\\\\\\\\) 써야 하거나, 슬래시(/)를 써야 합니다.")

        # [수정됨] 불필요한 Host, Port, Service Name 입력란을 제거했습니다.
        col1, col2 = st.columns(2)
        
        with col1:
            oracle_user = st.text_input(
                "사용자명 (User)",
                value=settings.database.oracle_user,
                key="ora_user"
            )
            oracle_dsn = st.text_input(
                "DSN (tnsnames.ora 별칭)",
                value=settings.database.oracle_dsn,
                help="예: snowbot_high, snowbot_low 등",
                key="ora_dsn"
            )
            
        with col2:
            oracle_password = st.text_input(
                "비밀번호 (Password)",
                value=settings.database.oracle_password,
                type="password",
                key="ora_pw"
            )
            oracle_wallet_path = st.text_input(
                "지갑 경로 (Wallet Path)",
                value=settings.database.oracle_wallet_path,
                help="압축 해제된 지갑 폴더의 전체 경로",
                key="ora_wallet"
            )

        if st.button("저장 (Oracle)", key="save_oracle"):
            settings_manager.update_database(
                db_type="oracle",
                oracle_user=oracle_user,
                oracle_password=oracle_password,
                oracle_dsn=oracle_dsn,
                oracle_wallet_path=oracle_wallet_path
                # oracle_host, oracle_port 등은 업데이트 안 함
            )
            st.success("Oracle 설정이 저장되었습니다.")
    
    st.divider()
    
    # DB 초기화
    st.markdown("#### 데이터 관리")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ 수집 데이터 삭제", key="del_collect"):
            st.session_state.del_confirm_type = "collect"
    
    with col2:
        if st.button("🗑️ 평가 데이터 삭제", key="del_eval"):
            st.session_state.del_confirm_type = "eval"
    
    with col3:
        if st.button("🗑️ 전체 초기화", type="secondary", key="del_all"):
            st.session_state.del_confirm_type = "all"
    
    # 삭제 확인
    if 'del_confirm_type' in st.session_state:
        del_type = st.session_state.del_confirm_type
        
        if del_type == "collect":
            st.warning("⚠️ 모든 수집 데이터(종목, 시세, 재무)를 삭제하시겠습니까?")
        elif del_type == "eval":
            st.warning("⚠️ 모든 평가 데이터를 삭제하시겠습니까?")
        else:
            st.error("🚨 모든 데이터를 삭제하고 DB를 초기화하시겠습니까?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 확인", key="confirm_del"):
                delete_data(del_type)
                del st.session_state.del_confirm_type
                st.success("✅ 삭제가 완료되었습니다.")
                st.rerun()
        with col2:
            if st.button("❌ 취소", key="cancel_del"):
                del st.session_state.del_confirm_type
                st.rerun()


def delete_data(del_type: str):
    """데이터 삭제"""
    from config.database import (
        ItemMst, ItemPrice, ItemEquity, FinancialSheet, 
        EvaluationResult, TradeHistory, Holdings
    )
    
    try:
        with get_session() as session:
            if del_type == "collect":
                session.query(FinancialSheet).delete()
                session.query(ItemEquity).delete()
                session.query(ItemPrice).delete()
                session.query(ItemMst).delete()
            elif del_type == "eval":
                session.query(EvaluationResult).delete()
            else:  # all
                session.query(TradeHistory).delete()
                session.query(Holdings).delete()
                session.query(EvaluationResult).delete()
                session.query(FinancialSheet).delete()
                session.query(ItemEquity).delete()
                session.query(ItemPrice).delete()
                session.query(ItemMst).delete()
    except Exception as e:
        st.error(f"삭제 오류: {e}")


def render_trading_settings(settings_manager, settings):
    """매매 설정 탭"""
    st.subheader("매매 설정")
    
    # 평가 설정
    st.markdown("#### 📊 평가 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_score = st.slider(
            "최소 매수 점수 (40점 만점)",
            min_value=0,
            max_value=40,
            value=settings.evaluation.min_total_score
        )
    
    with col2:
        st.info(f"현재 설정: {min_score}점 이상 → 매수 후보")
    
    # 지표별 가중치 설정
    st.markdown("##### 📈 지표별 가중치")
    st.caption("가중치가 높을수록 해당 지표가 총점에 더 큰 영향을 미칩니다. (기본값: 1.0)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        weight_sheet = st.number_input(
            "재무 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_sheet,
            step=0.1,
            key="weight_sheet"
        )
        
        weight_trend = st.number_input(
            "모멘텀 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_trend,
            step=0.1,
            key="weight_trend"
        )
    
    with col2:
        weight_price = st.number_input(
            "주가 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_price,
            step=0.1,
            key="weight_price"
        )
        
        weight_kpi = st.number_input(
            "KPI 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_kpi,
            step=0.1,
            key="weight_kpi"
        )
    
    with col3:
        weight_buy = st.number_input(
            "수급 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_buy,
            step=0.1,
            key="weight_buy"
        )
        
        weight_avls = st.number_input(
            "시총 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_avls,
            step=0.1,
            key="weight_avls"
        )
    
    with col4:
        weight_per = st.number_input(
            "PER 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_per,
            step=0.1,
            key="weight_per"
        )
        
        weight_pbr = st.number_input(
            "PBR 가중치",
            min_value=0.0,
            max_value=3.0,
            value=settings.evaluation.weight_pbr,
            step=0.1,
            key="weight_pbr"
        )
    
    st.divider()
    
    # 매매 설정
    st.markdown("#### 💹 매매 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**매수 설정**")
        
        buy_rate = st.slider(
            "1회 매수 비율 (총 투자금 대비 %)",
            min_value=0.0,
            max_value=100.0,
            value=settings.trading.buy_rate,
            step=1.0,
            help="총 투자금에서 1회 매수 시 사용할 비율"
        )
        
        max_buy_amount = st.number_input(
            "종목당 최대 매수 금액 (원)",
            min_value=100_000,
            max_value=10_000_000,
            value=settings.trading.max_buy_amount,
            step=100_000,
            help="한 종목에 투자할 수 있는 최대 금액"
        )
        
        limit_count = st.number_input(
            "최대 보유 종목 수",
            min_value=1,
            max_value=50,
            value=settings.trading.limit_count
        )
    
    with col2:
        st.markdown("**매도 설정**")
        
        sell_up_rate = st.slider(
            "목표 수익률 (%)",
            min_value=1.0,
            max_value=50.0,
            value=settings.trading.sell_up_rate,
            step=0.5
        )
        
        sell_down_rate = st.slider(
            "손절 기준 (%)",
            min_value=-50.0,
            max_value=-1.0,
            value=settings.trading.sell_down_rate,
            step=0.5
        )
        
        sell_hold_rate = st.slider(
            "매도 보류 비율 (%)",
            min_value=0.0,
            max_value=100.0,
            value=settings.trading.sell_hold_rate,
            step=5.0,
            help="종목당 최대 매수금액의 N% 도달 전까지 매도 제외"
        )
    
    st.divider()
    
    if st.button("💾 매매 설정 저장", type="primary", key="save_trading"):
        settings_manager.update_evaluation(
            min_total_score=min_score,
            weight_sheet=weight_sheet,
            weight_trend=weight_trend,
            weight_price=weight_price,
            weight_kpi=weight_kpi,
            weight_buy=weight_buy,
            weight_avls=weight_avls,
            weight_per=weight_per,
            weight_pbr=weight_pbr
        )
        settings_manager.update_trading(
            buy_rate=buy_rate,
            max_buy_amount=max_buy_amount,
            limit_count=limit_count,
            sell_up_rate=sell_up_rate,
            sell_down_rate=sell_down_rate,
            sell_hold_rate=sell_hold_rate
        )
        st.success("✅ 매매 설정이 저장되었습니다.")