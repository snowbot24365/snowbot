"""
공통 UI 컴포넌트
- 계좌 정보 표시 (시뮬레이션 DB / KIS API 연동)
- 로그 그리드
- 페이징 컴포넌트
- 장 운영 정보
- 공통 스케줄 설정 (render_schedule_config)
"""

import streamlit as st
from datetime import datetime, date, time as dt_time
from typing import List, Dict, Optional
import requests
import logging

import holidays

from config.database import get_session, VirtualAccount, VirtualHolding
from data.price_fetcher import KISAPIFetcher

logger = logging.getLogger(__name__)


def render_account_info(settings_manager):
    """계좌 정보 표시 (시뮬레이션/모의투자/실계좌 구분)"""
    settings = settings_manager.settings
    mode = settings.execution_mode
    api_mode = settings.api.kis_api_mode
    
    # 계좌 유형 및 스타일 결정
    if mode == "simulation":
        account_type = "simulation"
        account_label = "🎮 시뮬레이션 계좌"
        bg_color = "#f0f2f6" 
        border_color = "#d1d5db"
        text_color = "#1f2937"
        account_no = "SIMULATION"
        
        # 시뮬레이션 데이터 조회
        deposit, total_eval, profit, profit_rate, holdings_cnt = _get_simulation_account_info()
        
    elif settings.api.kis_trading_account_mode == "real" and mode == "real_trading":
        account_type = "real"
        account_label = "💰 실전투자 계좌 (실거래)"
        bg_color = "#fee2e2" 
        border_color = "#ef4444"
        text_color = "#991b1b"
        account_no = settings.api.kis_real_account_no or "미설정"
        
        # 실전투자 API 잔고 조회
        deposit, total_eval, profit, profit_rate, holdings_cnt = _get_kis_account_info("real", settings)
        
    else: # mock (default) or real_trading but mock account
        account_type = "mock"
        account_label = "🧪 모의투자 계좌"
        bg_color = "#dbeafe" 
        border_color = "#3b82f6"
        text_color = "#1e40af"
        account_no = settings.api.kis_mock_account_no or "미설정"
        
        # 모의투자 API 잔고 조회
        deposit, total_eval, profit, profit_rate, holdings_cnt = _get_kis_account_info("mock", settings)
    
    # CSS 스타일 적용
    st.markdown(f"""
    <style>
    .account-info-box {{
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: {bg_color};
        border: 1px solid {border_color};
        color: {text_color};
        margin-bottom: 1rem;
    }}
    .account-info-box h4 {{
        margin: 0;
        color: {text_color};
        font-size: 1rem;
        font-weight: 600;
    }}
    .account-info-box .account-no {{
        font-size: 0.875rem;
        opacity: 0.9;
    }}
    .metric-value {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {text_color};
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: {text_color};
        opacity: 0.8;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # 계좌 정보 표시 컨테이너
    st.markdown(f'<div class="account-info-box">', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 1])
    
    with col1:
        st.markdown(f"<h4>{account_label}</h4>", unsafe_allow_html=True)
        st.markdown(f'<span class="account-no">계좌번호: {account_no}</span>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<div class="metric-label">예수금</div><div class="metric-value">{deposit:,.0f}원</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'<div class="metric-label">총평가금액</div><div class="metric-value">{total_eval:,.0f}원</div>', unsafe_allow_html=True)
        
    with col4:
        # 수익일 때 빨간색, 손실일 때 파란색
        color_style = ""
        if profit > 0:
            color_style = "color: #ef4444;"  # Red
        elif profit < 0:
            color_style = "color: #3b82f6;"  # Blue
            
        st.markdown(f'<div class="metric-label">손익(수익률)</div><div class="metric-value" style="{color_style}">{profit:,.0f}원 ({profit_rate:+.2f}%)</div>', unsafe_allow_html=True)

    with col5:
        st.markdown(f'<div class="metric-label">보유종목</div><div class="metric-value">{holdings_cnt}개</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return account_type


def _get_simulation_account_info():
    """시뮬레이션 계좌 정보 조회 (DB)"""
    try:
        with get_session() as session:
            account = session.query(VirtualAccount).first()
            holdings_cnt = session.query(VirtualHolding).count()
            
            if account:
                deposit = account.balance
                total_eval = account.total_eval
                profit = account.total_profit
                profit_rate = account.total_profit_rate
                return deposit, total_eval, profit, profit_rate, holdings_cnt
            else:
                return 0, 0, 0, 0.0, 0
    except Exception as e:
        logger.error(f"시뮬레이션 계좌 조회 오류: {e}")
        return 0, 0, 0, 0.0, 0


def _get_kis_account_info(mode: str, settings):
    """KIS API 잔고 조회 (실전/모의)"""
    try:
        # KIS API Fetcher 사용
        fetcher = KISAPIFetcher(mode=mode)
        
        if not fetcher.is_configured():
            return 0, 0, 0, 0.0, 0
        
        # 토큰 확인 및 발급
        token = fetcher.get_access_token()
        if not token:
            logger.warning(f"[{mode}] KIS API 토큰 발급 실패로 잔고 조회 중단")
            return 0, 0, 0, 0.0, 0
            
        # 계좌번호 확인
        if mode == 'real':
            cano = settings.api.kis_real_account_no
            acnt_prdt_cd = settings.api.kis_real_account_cd
        else:
            cano = settings.api.kis_mock_account_no
            acnt_prdt_cd = settings.api.kis_mock_account_cd
            
        if not cano or not acnt_prdt_cd:
            return 0, 0, 0, 0.0, 0
            
        # Fetcher의 get_account_balance 호출
        balance_info = fetcher.get_account_balance(cano, acnt_prdt_cd)
        
        if balance_info:
            return (
                balance_info['deposit'],
                balance_info['total_eval'],
                balance_info['profit'],
                balance_info['profit_rate'],
                balance_info['holdings_count']
            )
            
        return 0, 0, 0, 0.0, 0
        
    except Exception as e:
        logger.error(f"KIS 계좌 조회 오류: {e}")
        return 0, 0, 0, 0.0, 0
    

def render_market_status():
    """장 운영 정보 표시"""
    now = datetime.now()
    today = now.date()
    current_time = now.time()
    
    # 한국 공휴일 체크
    kr_holidays = holidays.KR()
    
    # 주말 체크
    is_weekend = today.weekday() >= 5
    
    # 공휴일 체크
    is_holiday = today in kr_holidays
    
    # 장 시간 체크 (09:00 ~ 15:30)
    market_open = dt_time(9, 0)
    market_close = dt_time(15, 30)
    is_market_hours = market_open <= current_time <= market_close
    
    # 상태 결정
    if is_weekend:
        status = "휴장 (주말)"
        status_color = "🔴"
    elif is_holiday:
        holiday_name = kr_holidays.get(today, "공휴일")
        status = f"휴장 ({holiday_name})"
        status_color = "🔴"
    elif is_market_hours:
        status = "장 운영 중"
        status_color = "🟢"
    elif current_time < market_open:
        status = "장 시작 전"
        status_color = "🟡"
    else:
        status = "장 마감"
        status_color = "🟡"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"📅 **오늘 날짜**: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]})")
    
    with col2:
        st.info(f"🕐 **현재 시간**: {current_time.strftime('%H:%M:%S')}")
    
    with col3:
        if status_color == "🟢":
            st.success(f"{status_color} **{status}**")
        elif status_color == "🔴":
            st.error(f"{status_color} **{status}**")
        else:
            st.warning(f"{status_color} **{status}**")
    
    return {
        'is_market_open': is_market_hours and not is_weekend and not is_holiday,
        'is_trading_day': not is_weekend and not is_holiday,
        'status': status
    }


def render_log_grid(
    logs: List[Dict],
    task_type_filter: Optional[str] = None,
    show_filter: bool = True,
    height: int = 300
):
    """실행 로그 그리드 (필터링 기능 포함)"""
    if not logs:
        st.info("실행 로그가 없습니다.")
        return
    
    # 필터링 옵션
    if show_filter:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            task_types = ["전체"] + list(set(log.get('task_type', '') for log in logs))
            default_idx = 0
            if task_type_filter and task_type_filter in task_types:
                default_idx = task_types.index(task_type_filter)
            
            selected_type = st.selectbox(
                "작업 유형",
                task_types,
                index=default_idx,
                key=f"log_filter_type_{id(logs)}"
            )
        
        with col2:
            statuses = ["전체", "success", "failed", "running"]
            selected_status = st.selectbox(
                "상태",
                statuses,
                key=f"log_filter_status_{id(logs)}"
            )
    else:
        selected_type = task_type_filter or "전체"
        selected_status = "전체"
    
    # 필터 적용
    filtered_logs = logs
    if selected_type != "전체":
        filtered_logs = [log for log in filtered_logs if log.get('task_type') == selected_type]
    if selected_status != "전체":
        filtered_logs = [log for log in filtered_logs if log.get('status') == selected_status]
    
    # 그리드 데이터 변환
    log_data = []
    for log in filtered_logs:
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'running': '🔄'
        }.get(log.get('status', ''), '⚪')
        
        log_data.append({
            "상태": f"{status_emoji} {log.get('status', '')}",
            "작업": log.get('task_type', ''),
            "이름": log.get('schedule_name', ''),
            "시작": log.get('start_time', '')[:19] if log.get('start_time') else "",
            "종료": log.get('end_time', '')[:19] if log.get('end_time') else "",
            "메시지": log.get('message') or log.get('error_message') or ""
        })
    
    if log_data:
        st.dataframe(log_data, width="stretch", hide_index=True, height=height)
    else:
        st.info("필터 조건에 맞는 로그가 없습니다.")


def render_data_grid_with_paging(
    data: List[Dict],
    columns: List[str],
    page_size: int = 20,
    key_prefix: str = "grid"
):
    """페이징이 적용된 데이터 그리드"""
    if not data:
        st.info("조회된 데이터가 없습니다.")
        return
    
    total_count = len(data)
    total_pages = (total_count + page_size - 1) // page_size
    
    # 페이지 상태 관리
    page_key = f"{key_prefix}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    
    current_page = st.session_state[page_key]
    
    # 페이징 컨트롤
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ 처음", key=f"{key_prefix}_first", disabled=current_page == 1):
            st.session_state[page_key] = 1
            st.rerun()
    
    with col2:
        if st.button("◀️ 이전", key=f"{key_prefix}_prev", disabled=current_page == 1):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    
    with col3:
        st.markdown(f"<center>페이지 **{current_page}** / {total_pages} (총 {total_count}건)</center>", unsafe_allow_html=True)
    
    with col4:
        if st.button("다음 ▶️", key=f"{key_prefix}_next", disabled=current_page >= total_pages):
            st.session_state[page_key] = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("마지막 ⏭️", key=f"{key_prefix}_last", disabled=current_page >= total_pages):
            st.session_state[page_key] = total_pages
            st.rerun()
    
    # 현재 페이지 데이터 추출
    start_idx = (current_page - 1) * page_size
    end_idx = start_idx + page_size
    page_data = data[start_idx:end_idx]
    
    # 데이터프레임 표시
    display_data = []
    for row in page_data:
        display_row = {}
        for col in columns:
            display_row[col] = row.get(col, '')
        display_data.append(display_row)
    
    st.dataframe(display_data, width="stretch", hide_index=True)


def render_schedule_config(
    task_type: str,
    schedule_key: str,
    default_cron: str = "0 18 * * 1-5" # 기본값을 오후 6시로 변경
):
    """스케줄 설정 컴포넌트"""
    from scheduler.task_manager import get_scheduler
    
    st.markdown("#### 📅 스케줄 설정")
    
    # [수정] 1. 일반 작업용 프리셋 (수집/평가용 - 장 마감 후 위주)
    # 데이터 수집이 오래(약 5시간) 걸리므로 장 마감 직후나 야간 시간대 권장
    default_presets = {
        "매일 오후 4시 (장 마감 직후)": "0 16 * * *",
        "매일 오후 6시 (데이터 안정)": "0 18 * * *",
        "매일 밤 11시 (야간 작업)": "0 23 * * *",
        "매일 새벽 2시 (서버 부하 ↓)": "0 2 * * *",
        "주말(토) 오전 10시": "0 10 * * 6",
        "사용자 정의": "custom"
    }

    # 2. 자동 매매용 프리셋 (장중 위주)
    auto_trade_presets = {
        "1분마다 (장중)": "*/1 9-15 * * 1-5",
        "5분마다 (장중)": "*/5 9-15 * * 1-5",
        "10분마다 (장중)": "*/10 9-15 * * 1-5",
        "20분마다 (장중)": "*/20 9-15 * * 1-5",
        "30분마다 (장중)": "*/30 9-15 * * 1-5",
        "1시간마다 (장중)": "0 9-15 * * 1-5",
        "사용자 정의": "custom"
    }

    # 안내 메시지 표시
    if task_type == "data_collection":
        st.info("ℹ️ **데이터 수집은 약 5시간 이상 소요될 수 있습니다. 장 마감 후(16:00 이후) 실행을 권장합니다.**")
    elif task_type == "auto_trade":
        st.info("ℹ️ **자동 매매는 평일 09:00 ~ 15:59 사이에만 동작하도록 설정하는 것을 권장합니다.**")
    
    scheduler = get_scheduler()
    
    # 기존 스케줄 조회
    schedules = scheduler.get_schedules()
    existing = [s for s in schedules if s.task_type == task_type]
    
    # 기존 스케줄 표시
    if existing:
        st.markdown("**등록된 스케줄:**")
        for sch in existing:
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.text(f"📌 {sch.name}")
            with col2:
                st.text(f"⏰ {sch.cron_expression}")
            with col3:
                enabled = sch.enabled
                st.text("✅ 활성" if enabled else "❌ 비활성")
            with col4:
                if st.button("삭제", key=f"del_sch_{sch.id}"):
                    scheduler.delete_schedule(sch.id)
                    st.success("스케줄이 삭제되었습니다.")
                    st.rerun()
    
    # 새 스케줄 추가
    with st.expander("➕ 새 스케줄 추가"):
        col1, col2 = st.columns(2)
        
        with col1:
            schedule_name = st.text_input(
                "스케줄 이름",
                value=f"{task_type}_schedule",
                key=f"{schedule_key}_name"
            )
        
        with col2:
            # 작업 유형에 따라 프리셋 교체
            if task_type == "auto_trade":
                cron_presets = auto_trade_presets
            else:
                cron_presets = default_presets
            
            preset = st.selectbox(
                "실행 시간",
                list(cron_presets.keys()),
                key=f"{schedule_key}_preset"
            )
        
        if preset == "사용자 정의":
            cron_expr = st.text_input(
                "Cron 표현식",
                value=default_cron,
                key=f"{schedule_key}_cron",
                help="분 시 일 월 요일 (예: 0 18 * * * = 매일 오후 6시)"
            )
        else:
            cron_expr = cron_presets[preset]
            st.caption(f"Cron: `{cron_expr}`")
        
        enabled = st.checkbox("활성화", value=True, key=f"{schedule_key}_enabled")
        
        if st.button("스케줄 추가", key=f"{schedule_key}_add", type="primary"):
            try:
                scheduler.add_schedule(
                    name=schedule_name,
                    task_type=task_type,
                    cron_expression=cron_expr,
                    enabled=enabled
                )
                st.success(f"스케줄이 추가되었습니다: {schedule_name}")
                st.rerun()
            except Exception as e:
                st.error(f"스케줄 추가 실패: {e}")


def render_log_section(task_type: str, title: str = "📜 최근 실행 로그"):
    """실행 로그 섹션 렌더링"""
    from config.database import get_session, ScheduleLog
    
    st.markdown(f"### {title}")
    
    # [수정 1] 버튼 영역 확보를 위해 비율 조정 (4:1 -> 3:1 또는 7:3 등상황에 맞게)
    # 버튼 두 개가 들어가야 하므로 오른쪽 공간을 좀 더 줍니다.
    col1, col2 = st.columns([7, 3]) 

    with col2:
        # [수정 2] 컬럼 안에 또 컬럼을 만들어(Nested Columns) 버튼을 가로 배치
        btn_col1, btn_col2 = st.columns(2, gap="small")
        
        with btn_col1:
            if st.button("🔄 새로고침", key=f"refresh_{task_type}", width="stretch"):
                st.rerun()
                
        with btn_col2:
            # 삭제 버튼은 위험하므로 type="primary"를 빼거나 빨간색 느낌(secondary) 유지
            if st.button("🗑️ 로그 삭제", key=f"clear_log_{task_type}", width="stretch"):
                clear_schedule_logs(task_type)
                st.rerun()
    
    # 로그 조회
    try:
        log_data = []
        
        with get_session() as session:
            logs = session.query(ScheduleLog).filter(
                ScheduleLog.task_type == task_type
            ).order_by(ScheduleLog.start_time.desc()).limit(20).all()
            
            # 세션 내에서 딕셔너리로 변환
            for log in logs:
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'running': '🔄'
                }.get(log.status, '⚪')
                
                log_data.append({
                    "상태": f"{status_emoji} {log.status or ''}",
                    "이름": log.schedule_name or "",
                    "시작": log.start_time.strftime('%Y-%m-%d %H:%M:%S') if log.start_time else "",
                    "종료": log.end_time.strftime('%H:%M:%S') if log.end_time else "",
                    "메시지": (log.message or log.error_message or "")[:50]
                })
        
        # 세션 밖에서 데이터 표시
        if log_data:
            st.dataframe(log_data, width="stretch", hide_index=True, height=250)
        else:
            st.info("실행 로그가 없습니다.")
                
    except Exception as e:
        st.warning(f"로그 조회 오류: {e}")


def clear_schedule_logs(task_type: str = None):
    """실행 로그 삭제"""
    from config.database import get_session, ScheduleLog
    
    try:
        with get_session() as session:
            if task_type:
                deleted = session.query(ScheduleLog).filter(
                    ScheduleLog.task_type == task_type
                ).delete()
            else:
                deleted = session.query(ScheduleLog).delete()
            
            session.commit()
            st.success(f"✅ 로그 {deleted}건이 삭제되었습니다.")
            st.rerun()
            
    except Exception as e:
        st.error(f"로그 삭제 오류: {e}")