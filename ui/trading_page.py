"""
매매 페이지 UI
- 수동 매수/매도
- 종목 분석
"""

import streamlit as st
from datetime import datetime

from config.settings import get_settings_manager
from config.database import get_session, ItemMst
from trading.simulator import SimulationEngine
from trading.strategy import TradingStrategy, TradeSignal
from data.price_fetcher import PriceFetcher


def render_trading():
    """매매 페이지 렌더링"""
    st.markdown('<div class="main-header">💹 매매</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    simulator = SimulationEngine()
    strategy = TradingStrategy()
    price_fetcher = PriceFetcher()
    
    # 계좌 요약
    account_info = simulator.get_account_info()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("예수금", f"{account_info.balance:,}원")
    with col2:
        st.metric("보유종목", f"{len(account_info.holdings)}개")
    with col3:
        st.metric("총평가", f"{account_info.total_eval:,}원")
    
    st.divider()
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["🔍 종목 분석", "📥 매수", "📤 매도"])
    
    # ========== 종목 분석 탭 ==========
    with tab1:
        st.subheader("종목 분석")
        
        # 종목 검색
        col1, col2 = st.columns([3, 1])
        
        with col1:
            stock_code = st.text_input(
                "종목코드 입력",
                placeholder="예: 005930",
                max_chars=6
            )
        
        with col2:
            st.write("")
            st.write("")
            analyze_btn = st.button("분석", type="primary", width="stretch")
        
        if analyze_btn and stock_code:
            with st.spinner("분석 중..."):
                # 현재가 조회
                price_info = price_fetcher.get_current_price(stock_code)
                
                if price_info:
                    # 종목 정보 표시
                    st.success(f"현재가: **{price_info['price']:,}원** ({price_info['change_rate']:+.2f}%)")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("시가", f"{price_info['open']:,}")
                    with col2:
                        st.metric("고가", f"{price_info['high']:,}")
                    with col3:
                        st.metric("저가", f"{price_info['low']:,}")
                    with col4:
                        st.metric("거래량", f"{price_info['volume']:,}")
                    
                    st.divider()
                    
                    # 전략 분석
                    decision = strategy.analyze_stock(stock_code)
                    
                    # 시그널 표시
                    signal_colors = {
                        TradeSignal.STRONG_BUY: "🟢",
                        TradeSignal.BUY: "🟢",
                        TradeSignal.HOLD: "🟡",
                        TradeSignal.SELL: "🔴",
                        TradeSignal.STRONG_SELL: "🔴"
                    }
                    
                    st.markdown(f"### {signal_colors.get(decision.signal, '⚪')} {decision.signal.value}")
                    
                    if decision.score > 0:
                        st.write(f"종목 점수: **{decision.score}점**")
                    
                    if decision.target_price > 0:
                        st.write(f"목표가: **{decision.target_price:,}원**")
                    
                    if decision.stop_loss_price > 0:
                        st.write(f"손절가: **{decision.stop_loss_price:,}원**")
                    
                    if decision.reasons:
                        st.markdown("#### 분석 사유")
                        for reason in decision.reasons:
                            st.write(f"- {reason}")
                    
                else:
                    st.error("종목 정보를 조회할 수 없습니다. 종목코드를 확인해주세요.")
    
    # ========== 매수 탭 ==========
    with tab2:
        st.subheader("수동 매수")
        
        col1, col2 = st.columns(2)
        
        with col1:
            buy_code = st.text_input(
                "종목코드",
                placeholder="예: 005930",
                max_chars=6,
                key="buy_code"
            )
            
            # 현재가 조회
            if buy_code:
                price_info = price_fetcher.get_current_price(buy_code)
                if price_info:
                    st.info(f"현재가: {price_info['price']:,}원")
                    current_price = price_info['price']
                else:
                    current_price = 0
            else:
                current_price = 0
        
        with col2:
            buy_qty = st.number_input(
                "매수 수량",
                min_value=1,
                max_value=10000,
                value=1,
                key="buy_qty"
            )
            
            buy_price = st.number_input(
                "매수 가격 (0=현재가)",
                min_value=0,
                value=0,
                key="buy_price"
            )
        
        # 예상 금액 계산
        if buy_code and buy_qty > 0:
            price = buy_price if buy_price > 0 else current_price
            if price > 0:
                amount = price * buy_qty
                fee = int(amount * settings_manager.settings.trading.fee_rate)
                total = amount + fee
                
                st.write(f"예상 금액: {amount:,}원 + 수수료 {fee:,}원 = **{total:,}원**")
                
                if total > account_info.balance:
                    st.error(f"잔고 부족! (보유: {account_info.balance:,}원)")
        
        if st.button("매수 주문", type="primary", key="buy_btn"):
            if not buy_code:
                st.error("종목코드를 입력해주세요.")
            else:
                with st.spinner("매수 처리 중..."):
                    result = simulator.buy(
                        item_cd=buy_code,
                        qty=buy_qty,
                        price=buy_price
                    )
                    
                    if result.success:
                        st.success(result.message)
                        st.balloons()
                    else:
                        st.error(result.message)
    
    # ========== 매도 탭 ==========
    with tab3:
        st.subheader("수동 매도")
        
        if account_info.holdings:
            # 보유 종목 선택
            holding_options = {
                f"{h.item_nm} ({h.item_cd}) - {h.qty}주": h
                for h in account_info.holdings
            }
            
            selected = st.selectbox(
                "매도할 종목 선택",
                options=list(holding_options.keys())
            )
            
            if selected:
                holding = holding_options[selected]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**종목코드:** {holding.item_cd}")
                    st.write(f"**보유수량:** {holding.qty}주")
                    st.write(f"**평균단가:** {holding.avg_price:,}원")
                
                with col2:
                    st.write(f"**현재가:** {holding.current_price:,}원")
                    profit_emoji = "🔴" if holding.profit > 0 else "🔵"
                    st.write(f"**평가손익:** {profit_emoji} {holding.profit:+,}원 ({holding.profit_rate:+.2f}%)")
                
                st.divider()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    sell_qty = st.number_input(
                        "매도 수량",
                        min_value=1,
                        max_value=holding.qty,
                        value=holding.qty,
                        key="sell_qty"
                    )
                
                with col2:
                    sell_price = st.number_input(
                        "매도 가격 (0=현재가)",
                        min_value=0,
                        value=0,
                        key="sell_price"
                    )
                
                # 예상 금액 계산
                price = sell_price if sell_price > 0 else holding.current_price
                if price > 0:
                    amount = price * sell_qty
                    fee = int(amount * settings_manager.settings.trading.fee_rate)
                    tax = int(amount * settings_manager.settings.trading.tax_rate)
                    total = amount - fee - tax
                    
                    # 예상 손익
                    cost = holding.avg_price * sell_qty
                    expected_profit = total - cost
                    expected_rate = (expected_profit / cost * 100) if cost else 0
                    
                    st.write(f"예상 수령액: {amount:,}원 - 수수료 {fee:,}원 - 세금 {tax:,}원 = **{total:,}원**")
                    
                    profit_emoji = "🔴" if expected_profit > 0 else "🔵"
                    st.write(f"예상 손익: {profit_emoji} **{expected_profit:+,}원** ({expected_rate:+.2f}%)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("매도 주문", type="primary", key="sell_btn"):
                        with st.spinner("매도 처리 중..."):
                            result = simulator.sell(
                                item_cd=holding.item_cd,
                                qty=sell_qty,
                                price=sell_price
                            )
                            
                            if result.success:
                                st.success(result.message)
                                st.balloons()
                            else:
                                st.error(result.message)
                
                with col2:
                    if st.button("전량 매도", type="secondary", key="sell_all_btn"):
                        with st.spinner("전량 매도 처리 중..."):
                            result = simulator.sell(
                                item_cd=holding.item_cd,
                                qty=0,  # 0 = 전량
                                price=0
                            )
                            
                            if result.success:
                                st.success(result.message)
                                st.balloons()
                            else:
                                st.error(result.message)
                
                # 매도 분석
                st.divider()
                st.markdown("#### 매도 분석")
                
                sell_decision = strategy.analyze_holding_for_sell(
                    item_cd=holding.item_cd,
                    avg_price=holding.avg_price
                )
                
                signal_colors = {
                    TradeSignal.STRONG_BUY: "🟢",
                    TradeSignal.BUY: "🟢",
                    TradeSignal.HOLD: "🟡",
                    TradeSignal.SELL: "🔴",
                    TradeSignal.STRONG_SELL: "🔴"
                }
                
                st.markdown(f"**추천:** {signal_colors.get(sell_decision.signal, '⚪')} {sell_decision.signal.value}")
                
                if sell_decision.reasons:
                    for reason in sell_decision.reasons:
                        st.write(f"- {reason}")
        
        else:
            st.info("보유 종목이 없습니다.")
    
    # 하단에 전체 매도 버튼
    st.divider()
    
    with st.expander("⚠️ 위험 작업"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 전체 청산", type="secondary"):
                st.session_state.confirm_liquidate = True
        
        with col2:
            if st.button("🗑️ 계좌 초기화", type="secondary"):
                st.session_state.confirm_reset = True
        
        if st.session_state.get('confirm_liquidate'):
            st.warning("정말 모든 보유 종목을 청산하시겠습니까?")
            if st.button("예, 전체 청산합니다", type="primary"):
                with st.spinner("전체 청산 중..."):
                    for holding in account_info.holdings:
                        simulator.sell(holding.item_cd, 0, 0)
                    st.success("전체 청산이 완료되었습니다.")
                    st.session_state.confirm_liquidate = False
                    st.rerun()
        
        if st.session_state.get('confirm_reset'):
            st.warning("정말 계좌를 초기화하시겠습니까? 모든 거래 기록과 보유 종목이 삭제됩니다.")
            if st.button("예, 초기화합니다", type="primary"):
                simulator.reset_account()
                st.success("계좌가 초기화되었습니다.")
                st.session_state.confirm_reset = False
                st.rerun()
