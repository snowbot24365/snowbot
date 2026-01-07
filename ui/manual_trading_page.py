"""
수동매매 페이지
- 계좌 정보 표시
- 수동 매수/매도 (그리드 선택 방식 통일)
- 매매 결과 조회 (페이징)
- 실행 로그
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
from sqlalchemy import func

from config.settings import get_settings_manager
from config.database import get_session, TradeHistory, Holdings, VirtualHolding, ScheduleLog, EvaluationResult, ItemMst, ItemPrice
from trading.strategy import TradingStrategy, TradeSignal
from data.price_fetcher import KISAPIFetcher
from ui.components import (
    render_account_info, 
    render_market_status, 
    render_log_grid, 
    render_data_grid_with_paging,
    render_log_section
)


def render_manual_trading():
    """수동매매 페이지 렌더링"""
    st.markdown('<div class="main-header">🖐️ 수동매매</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    
    # ========== 계좌 정보 ==========
    account_type = render_account_info(settings_manager)
    
    # ========== 장 운영 정보 ==========
    market_status = render_market_status()
    
    st.divider()
    
    # ========== 매매 날짜 (오늘 고정) ==========
    today = date.today()
    st.info(f"📅 매매 날짜: **{today.strftime('%Y-%m-%d')}** (오늘)")
    
    # ========== 매수/매도 탭 ==========
    tab1, tab2, tab3 = st.tabs(["💵 매수 (추천종목)", "💸 매도 (보유종목)", "📈 종목 분석", ])
    
    # ========== 매수 탭 (수정됨) ==========
    with tab1:
        render_buy_section(settings_manager, account_type)
    
    # ========== 매도 탭 ==========
    with tab2:
        render_sell_section(settings_manager, account_type)
    
    # ========== 종목 분석 탭 ==========
    with tab3:
        render_stock_analysis()
    
    st.divider()
    
    # ========== 실행 로그 ==========
    render_log_section("manual_trade", "📜 최근 실행 로그")
    
    st.divider()
    
    # ========== 매매 결과 조회 ==========
    st.markdown("### 📊 매매 결과 조회")
    
    render_trade_history_grid()


def render_stock_analysis():
    """종목 분석 섹션"""
    st.markdown("#### 📈 종목 분석")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        stock_code = st.text_input(
            "종목코드",
            max_chars=6,
            placeholder="005930",
            key="mt_stock_code"
        )
        
        if st.button("🔍 분석", key="mt_analyze"):
            if stock_code and len(stock_code) == 6:
                analyze_stock(stock_code)
            else:
                st.warning("올바른 종목코드를 입력해주세요.")
    
    with col2:
        if 'mt_analysis_result' in st.session_state:
            result = st.session_state.mt_analysis_result
            
            # TradeDecision 객체 속성 접근
            stock_name = getattr(result, 'item_nm', '')
            stock_code_val = getattr(result, 'item_cd', '')
            current_price = getattr(result, 'current_price', 0)
            score = getattr(result, 'score', 0)
            signal = getattr(result, 'signal', None)
            reasons = getattr(result, 'reasons', [])
            
            st.markdown(f"**{stock_name}** ({stock_code_val})")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("현재가", f"{current_price:,}원")
            with col_b:
                st.metric("평가점수", f"{score}점")
            with col_c:
                st.metric("목표가", f"{getattr(result, 'target_price', 0):,}원")
            
            # 매매 시그널 표시
            reason_text = ", ".join(reasons) if reasons else "분석 완료"
            
            if signal == TradeSignal.STRONG_BUY:
                st.success(f"📈 **강력 매수** - {reason_text}")
            elif signal == TradeSignal.BUY:
                st.success(f"📈 **매수 추천** - {reason_text}")
            elif signal == TradeSignal.SELL:
                st.error(f"📉 **매도 추천** - {reason_text}")
            elif signal == TradeSignal.STRONG_SELL:
                st.error(f"📉 **강력 매도** - {reason_text}")
            else:
                st.info(f"⏸️ **관망** - {reason_text}")


def analyze_stock(stock_code: str):
    """종목 분석 실행"""
    try:
        strategy = TradingStrategy()
        result = strategy.analyze_stock(stock_code)
        
        st.session_state.mt_analysis_result = result
        st.rerun()
        
    except Exception as e:
        st.error(f"분석 오류: {e}")


def get_buy_candidates(settings_manager):
    """
    매수 후보군 조회 (DB 전용 - 고속)
    ItemPrice에는 전일 데이터까지만 있으므로, 이를 가져와서 '전일종가'로 사용합니다.
    """
    try:
        with get_session() as session:
            # 1. 가장 최근 평가 날짜 조회
            latest_date = session.query(func.max(EvaluationResult.base_date)).scalar()
            
            if not latest_date:
                return [], None
            
            # 2. 해당 날짜의 평가 결과 조회 (상위 100개)
            min_score = settings_manager.settings.evaluation.min_total_score
            
            results = session.query(EvaluationResult).filter(
                EvaluationResult.base_date == latest_date,
                EvaluationResult.total_score >= min_score
            ).order_by(EvaluationResult.total_score.desc()).limit(100).all()
            
            data = []
            for r in results:
                # [중요] DB에서 가장 최근 가격 조회 -> 수집 주기에 따라 '전일 종가'가 됩니다.
                price_row = session.query(ItemPrice.stck_clpr).filter(
                    ItemPrice.item_cd == r.item_cd
                ).order_by(ItemPrice.trade_date.desc()).first()
                
                # 전일 종가 (데이터가 없으면 0)
                yesterday_close = price_row[0] if price_row else 0
                
                data.append({
                    'item_cd': r.item_cd,
                    'item_nm': r.item_nm,
                    'total_score': r.total_score,
                    'is_candidate': r.is_buy_candidate,
                    'ref_price': yesterday_close, # 참고용(전일종가)
                })
            
            return data, latest_date
            
    except Exception as e:
        st.error(f"매수 후보 조회 오류: {e}")
        return [], None


def render_buy_section(settings_manager, account_type):
    """매수 섹션 (Grid=전일종가, Detail=실시간가)"""
    st.markdown("#### 💵 수동 매수 (추천 종목)")
    
    # 1. 데이터 조회 (DB only)
    if 'mt_buy_candidates_df' not in st.session_state:
        with st.spinner("매수 추천 종목 조회 중..."):
            candidates, base_date = get_buy_candidates(settings_manager)
            
            if candidates:
                df = pd.DataFrame(candidates)
                # [수정] 컬럼명을 '전일종가'로 변경하여 오해를 방지
                display_df = df[['item_nm', 'item_cd', 'total_score', 'ref_price', 'is_candidate']].copy()
                display_df.columns = ['종목명', '종목코드', '점수', '전일종가', '매수추천']
                
                display_df['매수추천'] = display_df['매수추천'].apply(lambda x: '✅' if x else '')
                
                st.session_state.mt_buy_raw = candidates
                st.session_state.mt_buy_candidates_df = display_df
                st.session_state.mt_buy_base_date = base_date
            else:
                st.session_state.mt_buy_candidates_df = None
                st.session_state.mt_buy_raw = []

    # 2. 상단 정보
    col_info, col_refresh = st.columns([3, 1])
    with col_info:
        base_date = st.session_state.get('mt_buy_base_date')
        if base_date:
            formatted_date = f"{base_date[:4]}-{base_date[4:6]}-{base_date[6:]}"
            st.caption(f"평가 기준일: {formatted_date}")
            
    with col_refresh:
        if st.button("🔄 목록 새로고침", key="mt_refresh_buy", width="stretch"):
            keys_to_del = ['mt_buy_candidates_df', 'mt_buy_raw', 'mt_selected_buy_item', 'mt_realtime_price_cache']
            for k in keys_to_del:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

    df_display = st.session_state.mt_buy_candidates_df
    
    if df_display is None or df_display.empty:
        st.info("매수 추천 종목이 없습니다.")
        return

    st.info("👇 목록에서 종목을 선택하면 **실시간 시세**를 조회하여 주문창을 띄웁니다.")

    # 3. 그리드 표시 (전일종가 표시)
    event = st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "점수": st.column_config.NumberColumn(format="%d점"),
            "전일종가": st.column_config.NumberColumn(format="%d원"), # 명칭 변경
        },
        key="mt_buy_grid"
    )

    # 4. 선택 시 실시간 가격 조회 (API 호출)
    selected_item = None
    
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        
        if 'mt_buy_raw' in st.session_state:
            raw_item = st.session_state.mt_buy_raw[selected_idx]
            
            # 캐싱 키 확인
            prev_selected = st.session_state.get('mt_selected_buy_item')
            cached_price = st.session_state.get('mt_realtime_price_cache', 0)
            
            # 종목이 변경되었거나 가격 정보가 없으면 API 호출
            if not prev_selected or prev_selected['item_cd'] != raw_item['item_cd'] or cached_price == 0:
                
                with st.spinner(f"📡 '{raw_item['item_nm']}' 실시간 시세 조회 중..."):
                    realtime_price = 0
                    try:
                        api_mode = "real" if account_type == "real" else "mock"
                        fetcher = KISAPIFetcher(mode=api_mode)
                        stock_info = fetcher.get_stock_info(raw_item['item_cd'])
                        
                        if stock_info:
                            # 현재가 조회
                            realtime_price = int(stock_info.get('stck_prpr') or stock_info.get('stck_clpr') or 0)
                    except Exception:
                        pass
                    
                    # API 실패 시 전일종가(ref_price)라도 사용
                    if realtime_price == 0:
                        realtime_price = raw_item['ref_price']
                        
                    st.session_state.mt_realtime_price_cache = realtime_price
                    st.session_state.mt_selected_buy_item = raw_item
            
            selected_item = st.session_state.mt_selected_buy_item

    elif 'mt_selected_buy_item' in st.session_state:
        del st.session_state.mt_selected_buy_item
        if 'mt_realtime_price_cache' in st.session_state:
            del st.session_state.mt_realtime_price_cache
        selected_item = None

    # 5. 매수 주문 UI
    if selected_item:
        st.divider()
        st.markdown(f"##### 📈 매수 주문: **{selected_item['item_nm']}** ({selected_item['item_cd']})")
        
        # 세션에 저장된 실시간 가격 사용
        realtime_price = st.session_state.get('mt_realtime_price_cache', selected_item['ref_price'])
        
        # 전일 대비 등락 계산 (UI 디테일 추가)
        yesterday_price = selected_item['ref_price']
        if yesterday_price > 0:
            diff = realtime_price - yesterday_price
            diff_rate = (diff / yesterday_price) * 100
            diff_str = f"{diff:+,}원 ({diff_rate:+.2f}%)"
            diff_color = "red" if diff > 0 else "blue" if diff < 0 else "black"
        else:
            diff_str = "-"
            diff_color = "black"

        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("전일종가", f"{yesterday_price:,}원")
            c2.metric("현재가(실시간)", f"{realtime_price:,}원")
            c3.markdown(f"전일대비: :{diff_color}[{diff_str}]") # 전일 대비 등락 표시

            col1, col2 = st.columns(2)
            u_key = f"buy_{selected_item['item_cd']}"
            
            with col1:
                buy_quantity = st.number_input(
                    "매수 수량",
                    min_value=1, max_value=10000, value=1,
                    key=f"qty_{u_key}"
                )
            
            with col2:
                buy_price = st.number_input(
                    "매수 가격 (0=시장가)",
                    min_value=0, max_value=10000000, 
                    value=realtime_price, # 실시간 가격 자동 입력
                    step=100,
                    key=f"price_{u_key}"
                )
            
            if buy_price > 0:
                total = buy_price * buy_quantity
                st.info(f"💰 예상 매수금액: **{total:,}원**")
            else:
                st.info("💰 **시장가** 매수")

            if st.button("💵 매수 주문 실행", type="primary", width="stretch", key=f"btn_{u_key}"):
                 execute_buy_order(
                    settings_manager=settings_manager,
                    stock_code=selected_item['item_cd'],
                    quantity=buy_quantity,
                    price=buy_price,
                    account_type=account_type
                )
                              

def render_sell_section(settings_manager, account_type):
    """매도 섹션 (그리드 선택 방식 - 체크 풀림 방지 적용)"""
    st.markdown("#### 💸 수동 매도 (보유 종목)")
    
    # 1. 데이터 조회 및 DataFrame 객체 캐싱
    if 'mt_holdings_df' not in st.session_state:
        with st.spinner("보유 종목 조회 중..."):
            holdings = get_holdings(settings_manager, account_type)
            if holdings:
                df = pd.DataFrame(holdings)
                display_df = df[['item_nm', 'item_cd', 'quantity', 'profit_rate', 'current_price', 'avg_price']].copy()
                display_df.columns = ['종목명', '종목코드', '보유수량', '수익률', '현재가', '매입가']
                st.session_state.mt_holdings_raw = holdings 
                st.session_state.mt_holdings_df = display_df
            else:
                st.session_state.mt_holdings_df = None
                st.session_state.mt_holdings_raw = []

    # 2. 새로고침 버튼
    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 목록 새로고침", key="mt_refresh_holdings"):
            if 'mt_holdings_df' in st.session_state: del st.session_state.mt_holdings_df
            if 'mt_holdings_raw' in st.session_state: del st.session_state.mt_holdings_raw
            if 'mt_selected_item' in st.session_state: del st.session_state.mt_selected_item
            st.rerun()
    
    df_display = st.session_state.mt_holdings_df
    
    if df_display is None or df_display.empty:
        st.info("보유 종목이 없습니다.")
        return

    st.info("👇 목록에서 종목을 선택(체크)하면 아래에 매도 주문창이 표시됩니다.")

    # 3. 그리드 표시
    event = st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "수익률": st.column_config.NumberColumn(format="%.2f%%"),
            "현재가": st.column_config.NumberColumn(format="%d원"),
            "매입가": st.column_config.NumberColumn(format="%d원"),
            "보유수량": st.column_config.NumberColumn(format="%d주"),
        },
        key="mt_holdings_grid"
    )
    
    # 4. 선택된 종목 파악
    selected_item = None
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        if 'mt_holdings_raw' in st.session_state and len(st.session_state.mt_holdings_raw) > selected_idx:
            selected_item = st.session_state.mt_holdings_raw[selected_idx]
            st.session_state.mt_selected_item = selected_item
            
    elif 'mt_selected_item' in st.session_state:
        del st.session_state.mt_selected_item
        selected_item = None

    # 5. 매도 주문 UI 표시
    if selected_item:
        st.divider()
        st.markdown(f"##### 📉 매도 주문: **{selected_item['item_nm']}** ({selected_item['item_cd']})")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("보유수량", f"{selected_item['quantity']:,}주")
            c2.metric("현재가", f"{selected_item['current_price']:,}원")
            profit_color = "red" if selected_item['profit_rate'] > 0 else "blue"
            c3.markdown(f"수익률: :{profit_color}[{selected_item['profit_rate']:+.2f}%]")
            
            col1, col2 = st.columns(2)
            u_key = selected_item['item_cd']
            
            with col1:
                sell_quantity = st.number_input(
                    "매도 수량",
                    min_value=1,
                    max_value=selected_item['quantity'],
                    value=selected_item['quantity'],
                    key=f"mt_sell_qty_{u_key}"
                )
            
            with col2:
                sell_price = st.number_input(
                    "매도가격 (0=시장가)",
                    min_value=0,
                    max_value=10000000,
                    value=0,
                    step=100,
                    key=f"mt_sell_price_{u_key}"
                )
            
            if sell_price > 0:
                total = sell_price * sell_quantity
                st.info(f"💰 예상 매도금액: **{total:,}원**")
            else:
                st.info("💰 **시장가** 매도")
            
            b1, b2 = st.columns(2)
            with b1:
                if st.button("💸 매도 주문 실행", type="primary", width="stretch", key=f"btn_sell_{u_key}"):
                    success = execute_sell_order(
                        settings_manager=settings_manager,
                        stock_code=selected_item['item_cd'],
                        quantity=sell_quantity,
                        price=sell_price,
                        account_type=account_type
                    )
                    if success:
                        if 'mt_holdings_df' in st.session_state: del st.session_state.mt_holdings_df
                        if 'mt_holdings_raw' in st.session_state: del st.session_state.mt_holdings_raw
                        if 'mt_selected_item' in st.session_state: del st.session_state.mt_selected_item
                        time.sleep(0.5)
                        st.rerun()
                        
            with b2:
                if st.button("🔄 전량 시장가 매도", width="stretch", key=f"btn_all_{u_key}"):
                    success = execute_sell_order(
                        settings_manager=settings_manager,
                        stock_code=selected_item['item_cd'],
                        quantity=selected_item['quantity'],
                        price=0,
                        account_type=account_type
                    )
                    if success:
                        if 'mt_holdings_df' in st.session_state: del st.session_state.mt_holdings_df
                        if 'mt_holdings_raw' in st.session_state: del st.session_state.mt_holdings_raw
                        if 'mt_selected_item' in st.session_state: del st.session_state.mt_selected_item
                        time.sleep(0.5)
                        st.rerun()


def get_holdings(settings_manager, account_type):
    """보유 종목 조회 (DB 또는 API)"""
    # 1. 시뮬레이션: DB 조회
    if account_type == "simulation":
        try:
            with get_session() as session:
                holdings = session.query(VirtualHolding).filter(VirtualHolding.quantity > 0).all()
                if not holdings:
                    holdings = session.query(Holdings).filter(Holdings.quantity > 0).all()
                
                result = []
                for h in holdings:
                    current_price = h.avg_price # 시뮬레이션은 현재가 업데이트 로직 필요
                    profit_rate = ((current_price - h.avg_price) / h.avg_price * 100) if h.avg_price > 0 else 0
                    result.append({
                        'item_cd': h.item_cd,
                        'item_nm': h.item_nm or h.item_cd,
                        'quantity': h.quantity,
                        'avg_price': h.avg_price,
                        'current_price': current_price,
                        'profit_rate': profit_rate
                    })
                return result
        except:
            return []
            
    # 2. 실전/모의: API 조회
    else:
        try:
            settings = settings_manager.settings
            api_mode = "real" if account_type == "real" else "mock"
            
            fetcher = KISAPIFetcher(mode=api_mode)
            
            if api_mode == "real":
                acct_no = settings.api.kis_real_account_no
                acct_cd = settings.api.kis_real_account_cd
            else:
                acct_no = settings.api.kis_mock_account_no
                acct_cd = settings.api.kis_mock_account_cd
                
            balance = fetcher.get_account_balance(acct_no, acct_cd)
            
            result = []
            if balance and 'holdings' in balance:
                for h in balance['holdings']:
                    qty = int(h.get('hldg_qty', 0))
                    if qty > 0:
                        avg_price = float(h.get('pchs_avg_pric', 0))
                        cur_price = int(h.get('prpr', 0))
                        rate = float(h.get('evlu_pfls_rt', 0))
                        
                        result.append({
                            'item_cd': h.get('pdno', ''),
                            'item_nm': h.get('prdt_name', ''),
                            'quantity': qty,
                            'avg_price': avg_price,
                            'current_price': cur_price,
                            'profit_rate': rate
                        })
            return result
        except Exception as e:
            st.error(f"API 조회 오류: {e}")
            return []


def log_manual_trade(message: str, status: str = "success", error_msg: str = None):
    """수동 매매 로그 DB 저장"""
    try:
        with get_session() as session:
            log = ScheduleLog(
                schedule_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                schedule_name="수동매매",
                task_type="manual_trade",
                status=status,
                start_time=datetime.now(),
                end_time=datetime.now(),
                message=message,
                error_message=error_msg
            )
            session.add(log)
            session.commit()
    except Exception as e:
        print(f"로그 저장 실패: {e}")


def execute_buy_order(settings_manager, stock_code: str, quantity: int, price: int, account_type: str):
    """매수 주문 실행"""
    try:
        order_type = "시장가" if price == 0 else "지정가"
        st.info(f"매수 주문 전송 중... ({order_type})")
        
        # 1. 시뮬레이션
        if account_type == "simulation":
            from trading.simulator import SimulationEngine
            engine = SimulationEngine()
            result = engine.execute_buy(stock_code, quantity, price)
            
            if result['success']:
                st.success(f"✅ 매수 완료: {stock_code} {quantity}주 @ {result['executed_price']:,}원")
                save_trade_history(stock_code, 'buy', quantity, result['executed_price'], date.today())
                log_manual_trade(f"[매수] {stock_code} {quantity}주 @ {result['executed_price']:,}원 (시뮬레이션)")
            else:
                st.error(f"❌ 매수 실패: {result['message']}")
                log_manual_trade(f"[매수실패] {stock_code} {quantity}주 - {result['message']}", "failed", result['message'])
                
        # 2. 실전/모의투자 (API)
        else:
            settings = settings_manager.settings
            api_mode = "real" if account_type == "real" else "mock"
            
            if api_mode == "real":
                acct_no = settings.api.kis_real_account_no
                acct_cd = settings.api.kis_real_account_cd
            else:
                acct_no = settings.api.kis_mock_account_no
                acct_cd = settings.api.kis_mock_account_cd
                
            if not acct_no or not acct_cd:
                st.error("계좌 정보가 설정되지 않았습니다.")
                return

            fetcher = KISAPIFetcher(mode=api_mode)
            res = fetcher.send_order('buy', stock_code, quantity, price, acct_no, acct_cd)
            
            if res['success']:
                st.success(f"✅ 주문 전송 완료 (주문번호: {res['order_no']})")
                
                # 시장가(0)인 경우 현재가 조회하여 기록
                record_price = price
                if record_price == 0:
                    stock_info = fetcher.get_stock_info(stock_code)
                    if stock_info:
                        record_price = stock_info.get('stck_clpr', 0)
                
                save_trade_history(stock_code, 'buy', quantity, record_price, date.today())
                log_manual_trade(f"[매수] {stock_code} {quantity}주 ({order_type}) 주문전송")
            else:
                st.error(f"❌ 주문 실패: {res['message']}")
                log_manual_trade(f"[매수실패] {stock_code} {quantity}주 - {res['message']}", "failed", res['message'])
            
    except Exception as e:
        st.error(f"매수 주문 오류: {e}")
        log_manual_trade(f"[매수오류] {stock_code}", "failed", str(e))


def execute_sell_order(settings_manager, stock_code: str, quantity: int, price: int, account_type: str) -> bool:
    """매도 주문 실행 (성공 여부 반환)"""
    try:
        order_type = "시장가" if price == 0 else "지정가"
        st.info(f"매도 주문 전송 중... ({order_type})")
        
        # 1. 시뮬레이션
        if account_type == "simulation":
            from trading.simulator import SimulationEngine
            engine = SimulationEngine()
            result = engine.execute_sell(stock_code, quantity, price)
            
            if result['success']:
                st.success(f"✅ 매도 완료: {stock_code} {quantity}주 @ {result['executed_price']:,}원")
                save_trade_history(stock_code, 'sell', quantity, result['executed_price'], date.today())
                log_manual_trade(f"[매도] {stock_code} {quantity}주 @ {result['executed_price']:,}원 (시뮬레이션)")
                return True
            else:
                st.error(f"❌ 매도 실패: {result['message']}")
                log_manual_trade(f"[매도실패] {stock_code} {quantity}주 - {result['message']}", "failed", result['message'])
                return False
                
        # 2. 실전/모의투자 (API)
        else:
            settings = settings_manager.settings
            api_mode = "real" if account_type == "real" else "mock"
            
            if api_mode == "real":
                acct_no = settings.api.kis_real_account_no
                acct_cd = settings.api.kis_real_account_cd
            else:
                acct_no = settings.api.kis_mock_account_no
                acct_cd = settings.api.kis_mock_account_cd
                
            if not acct_no or not acct_cd:
                st.error("계좌 정보가 설정되지 않았습니다.")
                return False

            fetcher = KISAPIFetcher(mode=api_mode)
            res = fetcher.send_order('sell', stock_code, quantity, price, acct_no, acct_cd)
            
            if res['success']:
                st.success(f"✅ 주문 전송 완료 (주문번호: {res['order_no']})")
                
                # 시장가(0)인 경우 현재가 조회하여 기록
                record_price = price
                if record_price == 0:
                    stock_info = fetcher.get_stock_info(stock_code)
                    if stock_info:
                        record_price = stock_info.get('stck_clpr', 0)
                
                save_trade_history(stock_code, 'sell', quantity, record_price, date.today())
                log_manual_trade(f"[매도] {stock_code} {quantity}주 ({order_type}) 주문전송")
                return True
            else:
                st.error(f"❌ 주문 실패: {res['message']}")
                log_manual_trade(f"[매도실패] {stock_code} {quantity}주 - {res['message']}", "failed", res['message'])
                return False
            
    except Exception as e:
        st.error(f"매도 주문 오류: {e}")
        log_manual_trade(f"[매도오류] {stock_code}", "failed", str(e))
        return False


def save_trade_history(item_cd: str, trade_type: str, quantity: int, price: int, trade_date: date):
    """거래 기록 저장"""
    try:
        with get_session() as session:
            trade = TradeHistory(
                item_cd=item_cd,
                trade_type=trade_type,
                quantity=quantity,
                price=price,
                amount=quantity * price,
                trade_date=trade_date.strftime('%Y%m%d'),
                trade_time=datetime.now().strftime('%H%M%S'),
                created_at=datetime.now()
            )
            session.add(trade)
            session.commit()
    except Exception as e:
        st.error(f"거래 기록 저장 오류: {e}")


def render_trade_history_grid():
    """매매 결과 그리드"""
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_date = st.date_input(
            "조회 날짜",
            value=date.today(),
            max_value=date.today(),
            key="mt_query_date"
        )
    
    try:
        with get_session() as session:
            date_str = selected_date.strftime('%Y%m%d')
            
            query = session.query(TradeHistory).filter(
                TradeHistory.trade_date == date_str
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
                    "금액": f"{row.amount:,}원"
                })
            
            if data:
                st.markdown(f"**조회 결과: {len(data)}건**")
                
                render_data_grid_with_paging(
                    data=data,
                    columns=["시간", "종류", "종목코드", "수량", "단가", "금액"],
                    page_size=20,
                    key_prefix="mt_history"
                )
            else:
                st.info(f"{selected_date} 날짜의 매매 기록이 없습니다.")
                
    except Exception as e:
        st.error(f"데이터 조회 오류: {e}")