"""
자동매매 페이지
- 계좌 정보 표시
- 장 운영 정보
- 자동매매 실행
- 스케줄 설정
- 자동매매 결과 조회 (페이징)
- 실행 로그
"""

import streamlit as st
from datetime import datetime, date
import time
import pandas as pd

from config.settings import get_settings_manager
from config.database import get_session, TradeHistory, Holdings, VirtualHolding
from trading.strategy import TradingStrategy
from scheduler.task_manager import get_scheduler, TaskType
from data.price_fetcher import KISAPIFetcher
# [추가] AutoTrader 임포트
from trading.auto_trader import AutoTrader
from ui.components import (
    render_account_info,
    render_market_status,
    render_log_grid,
    render_data_grid_with_paging,
    render_schedule_config,
    render_log_section
)


def render_auto_trading():
    """자동매매 페이지 렌더링"""
    st.markdown('<div class="main-header">🤖 자동매매</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    settings = settings_manager.settings
    
    # ========== 계좌 정보 ==========
    account_type = render_account_info(settings_manager)
    
    # ========== 장 운영 정보 ==========
    market_status = render_market_status()
    
    st.divider()
    
    # ========== 매매 날짜 (오늘 고정) ==========
    today = date.today()
    st.info(f"📅 매매 날짜: **{today.strftime('%Y-%m-%d')}** (오늘)")
    
    # ========== 자동매매 설정 및 실행 ==========
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ⚙️ 자동매매 설정")
        
        trading_settings = settings.trading
        
        buy_enabled = st.checkbox(
            "매수 활성화",
            value=trading_settings.buy_enabled,
            key="at_buy_enabled"
        )
        
        st.markdown("**현재 설정:**")
        st.write(f"- 1회 최대 매수금액: **{trading_settings.max_buy_amount:,}원**")
        st.write(f"- 매수 비율: **{trading_settings.buy_rate}%** (예수금 대비)")
        st.write(f"- 익절선: **+{trading_settings.sell_up_rate}%**")
        st.write(f"- 손절선: **{trading_settings.sell_down_rate}%**")
        st.write(f"- 최대 보유: **{trading_settings.limit_count}종목**")
        
        if trading_settings.trailing_stop_enabled:
            st.write(f"- 트레일링 스탑: **{trading_settings.trailing_stop_rate}%**")
        
        if st.button("💾 설정 저장", key="at_save"):
            settings_manager.update_trading(buy_enabled=buy_enabled)
            st.success("✅ 설정이 저장되었습니다.")
    
    with col2:
        st.markdown("### 🚀 실행")
        
        # 실행 조건 체크
        can_trade = True
        warnings = []
        
        if not market_status['is_trading_day']:
            warnings.append("⚠️ 오늘은 휴장일입니다.")
            can_trade = False
        
        if not market_status['is_market_open']:
            warnings.append("⚠️ 현재 장 운영 시간이 아닙니다.")
        
        if account_type == "real" and not settings.api.kis_real_confirmed:
            warnings.append("⚠️ 실전투자 동의가 필요합니다.")
            can_trade = False
        
        for warn in warnings:
            st.warning(warn)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 실행 버튼
        if account_type == "real":
            st.error("🚨 **실계좌 모드** - 실제 자금으로 거래됩니다!")
            
            confirm = st.checkbox("실거래 자동매매를 실행합니다.", key="at_confirm")
            
            if st.button(
                "🚀 자동매매 실행 (1회)", 
                type="primary", 
                width="stretch", 
                key="at_run",
                disabled=not (can_trade and confirm)
            ):
                run_auto_trading_logic(account_type, settings_manager)
        else:
            if st.button(
                "🚀 자동매매 실행 (1회)", 
                type="primary", 
                width="stretch", 
                key="at_run",
                disabled=not can_trade
            ):
                run_auto_trading_logic(account_type, settings_manager)
        
        # 매매 중지 버튼 (스케줄러 중지 의미)
        st.markdown("<br>", unsafe_allow_html=True)
        
        scheduler = get_scheduler()
        if scheduler and scheduler.is_running():
             if st.button("⏹️ 스케줄러 중지", key="at_stop"):
                scheduler.stop()
                st.info("스케줄러가 중지되었습니다.")
                st.rerun()
        else:
             st.info("스케줄러가 현재 중지 상태입니다.")
    
    st.divider()
    
    # ========== 스케줄 설정 ==========
    render_schedule_config(
        task_type="auto_trade",
        schedule_key="at_schedule",
        default_cron="10 9 * * 1-5"
    )
    
    st.divider()
    
    # ========== 보유 종목 현황 ==========
    st.markdown("### 📋 보유 종목 현황")
    
    render_holdings_summary(settings_manager, account_type)
    
    st.divider()
    
    # ========== 실행 로그 ==========
    render_log_section("auto_trade", "📜 최근 실행 로그")
    
    st.divider()
    
    # ========== 자동매매 결과 조회 ==========
    st.markdown("### 📊 자동매매 결과 조회")
    
    render_auto_trade_history_grid()


def run_auto_trading_logic(account_type: str, settings_manager):
    """자동매매 로직 실행 (1회)"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    log_container = st.container()
    log_area = log_container.empty()
    log_messages = []
    
    def update_progress(current, total, message):
        progress = int((current / total) * 100) if total > 0 else 0
        progress_bar.progress(progress)
        status_text.text(f"[{progress}%] {message}")
    
    def update_log(message):
        log_messages.append(message)
        display_logs = log_messages[-20:]
        log_area.text_area(
            "실행 로그",
            value="\n".join(display_logs),
            height=300,
            key=f"at_log_{len(log_messages)}"
        )
    
    try:
        status_text.text("자동매매 로직 시작...")
        update_log(f"[시작] 자동매매 로직 실행 ({account_type} 모드)")
        
        # 진행률 업데이트 (초기)
        update_progress(10, 100, "매매 엔진 초기화 중...")
        
        # [수정] AutoTrader 인스턴스 생성 및 실행
        # AutoTrader 내부에서 설정(시뮬레이션/실전)을 확인하여 적절히 동작함
        trader = AutoTrader()
        
        # 실행 전 로그
        update_log("[준비] 계좌 잔고 조회 및 매매 조건 확인...")
        update_progress(30, 100, "매도/매수 조건 분석 중...")
        
        # 실제 로직 실행 (Blocking Call)
        # run() 메서드가 문자열로 된 로그를 반환함
        result_log = trader.run()
        
        # 결과 로그 파싱 및 출력
        for line in result_log.split('\n'):
            update_log(f"> {line}")
            time.sleep(0.1) # UI 업데이트 효과
            
        update_progress(100, 100, "완료")
        status_text.text("✅ 자동매매 로직 실행 완료")
        st.success("자동매매 로직이 완료되었습니다.")
        update_log("[종료] 로직 실행 종료")
        
    except Exception as e:
        progress_bar.progress(100)
        status_text.text(f"❌ 오류 발생")
        st.error(f"자동매매 오류: {e}")
        update_log(f"[오류] {e}")


def render_holdings_summary(settings_manager, account_type):
    """보유 종목 현황 (시뮬레이션/API 분기 처리 - Manual Page와 동일 로직 적용)"""
    settings = settings_manager.settings
    
    data = []
    total_buy_amount = 0
    total_eval_amount = 0
    
    # 1. 시뮬레이션 모드: DB 조회
    if account_type == "simulation":
        try:
            with get_session() as session:
                holdings = session.query(VirtualHolding).filter(VirtualHolding.quantity > 0).all()
                if not holdings:
                    holdings = session.query(Holdings).filter(Holdings.quantity > 0).all()
                
                if holdings:
                    for h in holdings:
                        current_price = h.avg_price # 시뮬레이션은 현재가 업데이트 필요
                        eval_amount = current_price * h.quantity
                        buy_amount = h.avg_price * h.quantity
                        profit_rate = ((current_price - h.avg_price) / h.avg_price * 100) if h.avg_price > 0 else 0
                        
                        total_buy_amount += buy_amount
                        total_eval_amount += eval_amount
                        
                        data.append({
                            "종목코드": h.item_cd,
                            "종목명": h.item_nm or h.item_cd,
                            "수량": f"{h.quantity:,}",
                            "평균단가": f"{h.avg_price:,}원",
                            "현재가": f"{current_price:,}원",
                            "평가금액": f"{eval_amount:,}원",
                            "수익률": f"{profit_rate:+.2f}%"
                        })
        except Exception as e:
            st.error(f"보유 종목 조회 오류 (DB): {e}")

    # 2. 실전/모의투자 모드: KIS API 조회
    else:
        try:
            api_mode = "real" if account_type == "real" else "mock"
            
            # API Fetcher 초기화
            fetcher = KISAPIFetcher(mode=api_mode)
            
            # 계좌번호 가져오기
            if api_mode == "real":
                account_no = settings.api.kis_real_account_no
                account_cd = settings.api.kis_real_account_cd
            else:
                account_no = settings.api.kis_mock_account_no
                account_cd = settings.api.kis_mock_account_cd
            
            if account_no and account_cd:
                # 잔고 조회 API 호출
                balance_info = fetcher.get_account_balance(account_no, account_cd)
                
                if balance_info and 'holdings' in balance_info:
                    holdings_list = balance_info['holdings'] # API의 output1
                    
                    for h in holdings_list:
                        item_cd = h.get('pdno', '')
                        item_nm = h.get('prdt_name', '')
                        qty = int(h.get('hldg_qty', 0))
                        avg_price = float(h.get('pchs_avg_pric', 0))
                        cur_price = int(h.get('prpr', 0))
                        eval_amt = int(h.get('evlu_amt', 0))
                        rate = float(h.get('evlu_pfls_rt', 0))
                        
                        # API에서 매입금액을 주지 않는 경우 계산
                        buy_amt = avg_price * qty
                        
                        total_buy_amount += buy_amt
                        total_eval_amount += eval_amt
                        
                        data.append({
                            "종목코드": item_cd,
                            "종목명": item_nm,
                            "수량": f"{qty:,}",
                            "평균단가": f"{int(avg_price):,}원",
                            "현재가": f"{cur_price:,}원",
                            "평가금액": f"{eval_amt:,}원",
                            "수익률": f"{rate:+.2f}%"
                        })
        except Exception as e:
            st.error(f"보유 종목 조회 오류 (API): {e}")

    # 데이터 출력
    if data:
        # 요약 정보 (API 모드일 때는 API에서 받은 값 or 합산 값 사용)
        total_profit_rate = ((total_eval_amount - total_buy_amount) / total_buy_amount * 100) if total_buy_amount > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("보유 종목수", f"{len(data)}개")
        with col2:
            st.metric("총 매입금액", f"{total_buy_amount:,.0f}원")
        with col3:
            st.metric("총 평가금액", f"{total_eval_amount:,.0f}원")
        with col4:
            color = "red" if total_profit_rate > 0 else "blue" if total_profit_rate < 0 else "off"
            st.markdown(f"""
            <div style="font-size: 0.8rem; color: gray;">총 수익률</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {'#ef4444' if total_profit_rate > 0 else '#3b82f6'};">
                {total_profit_rate:+.2f}%
            </div>
            """, unsafe_allow_html=True)
        
        st.dataframe(data, width="stretch", hide_index=True)
    else:
        st.info("보유 종목이 없습니다.")


def render_auto_trade_history_grid():
    """자동매매 결과 그리드"""
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_date = st.date_input(
            "조회 날짜",
            value=date.today(),
            max_value=date.today(),
            key="at_query_date"
        )
    
    try:
        with get_session() as session:
            date_str = selected_date.strftime('%Y%m%d')
            
            # 자동매매 거래 내역 조회
            query = session.query(TradeHistory).filter(
                TradeHistory.trade_date == date_str,
                TradeHistory.trade_source == 'auto'  # 자동매매 구분
            ).order_by(TradeHistory.created_at.desc()).all()
            
            data = []
            for row in query:
                trade_type_kr = "매수" if row.trade_type == 'buy' else "매도"
                data.append({
                    "시간": row.trade_time[:4] if row.trade_time else "",
                    "종류": f"{'🟢' if row.trade_type == 'buy' else '🔴'} {trade_type_kr}",
                    "종목코드": row.item_cd,
                    "수량": f"{row.quantity:,}",
                    "단가": f"{row.price:,}원",
                    "금액": f"{row.amount:,}원",
                    "사유": row.trade_reason or ""
                })
            
            if data:
                st.markdown(f"**조회 결과: {len(data)}건**")
                
                render_data_grid_with_paging(
                    data=data,
                    columns=["시간", "종류", "종목코드", "수량", "단가", "금액", "사유"],
                    page_size=20,
                    key_prefix="at_history"
                )
            else:
                st.info(f"{selected_date} 날짜의 자동매매 기록이 없습니다.")
                
    except Exception as e:
        st.error(f"데이터 조회 오류: {e}")