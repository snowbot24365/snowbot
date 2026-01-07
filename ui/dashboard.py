"""
대시보드 페이지
- 전체 시스템 현황 요약
- 계좌 잔고 및 보유 종목 현황
- 데이터 수집/평가 현황
- 매수 후보 종목 리스트
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc

from config.settings import get_settings_manager
from config.database import get_session, ItemMst, ItemPrice, EvaluationResult, VirtualHolding, Holdings
from data.price_fetcher import KISAPIFetcher
from ui.components import render_account_info

def render_dashboard():
    """대시보드 렌더링"""
    st.markdown('<div class="main-header">📊 대시보드</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    settings = settings_manager.settings
    
    # 1. 계좌 정보 (요약 박스)
    st.markdown("### 💰 계좌 현황")
    render_account_info(settings_manager)
    
    # 2. 보유 종목 상세 현황 (테이블)
    render_holdings_detail(settings_manager)
    
    st.divider()
    
    # 3. 데이터 및 평가 현황
    st.markdown("### 📈 데이터 및 평가 현황")
    
    # 통계 데이터 계산
    stats = calculate_statistics(settings)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 관리 종목", f"{stats['total_items']:,}개")
        
    with col2:
        date_display = f"({stats['latest_eval_date']})" if stats['latest_eval_date'] else ""
        st.metric(f"총 평가 완료 {date_display}", f"{stats['evaluated_count']:,}개")
        
    with col3:
        st.metric("매수 후보", f"{stats['buy_candidates_count']:,}개", help=f"평가점수 {settings.evaluation.min_total_score}점 이상")
    
    # 4. 매수 후보 상세 (테이블)
    if stats['buy_candidates_count'] > 0:
        st.markdown("#### 🎁 매수 후보 리스트 (Top 20)")
        render_buy_candidates_table(stats['latest_eval_date'], settings.evaluation.min_total_score)
    else:
        st.info("현재 매수 후보 종목이 없습니다.")


def calculate_statistics(settings):
    """대시보드 통계 데이터 계산"""
    stats = {
        'total_items': 0,
        'evaluated_count': 0,
        'buy_candidates_count': 0,
        'latest_eval_date': None
    }
    
    try:
        with get_session() as session:
            # 1. 총 관리 종목 수
            stats['total_items'] = session.query(ItemMst).count()
            
            # 2. 가장 최근 평가 날짜 조회
            latest_date = session.query(func.max(EvaluationResult.base_date)).scalar()
            
            if latest_date:
                stats['latest_eval_date'] = latest_date
                
                # 3. 최근 평가 종목 수
                stats['evaluated_count'] = session.query(EvaluationResult).filter(
                    EvaluationResult.base_date == latest_date
                ).count()
                
                # 4. 매수 후보 수 (기준 점수 이상)
                min_score = settings.evaluation.min_total_score
                stats['buy_candidates_count'] = session.query(EvaluationResult).filter(
                    EvaluationResult.base_date == latest_date,
                    EvaluationResult.total_score >= min_score
                ).count()
                
    except Exception as e:
        st.error(f"통계 계산 오류: {e}")
        
    return stats


def render_holdings_detail(settings_manager):
    """보유 종목 상세 리스트 출력"""
    account_type = settings_manager.settings.execution_mode
    holdings_data = []
    
    # 1. 시뮬레이션 모드: DB 조회
    if account_type == "simulation":
        try:
            with get_session() as session:
                # VirtualHolding 우선, 없으면 Holdings
                holdings = session.query(VirtualHolding).filter(VirtualHolding.quantity > 0).all()
                if not holdings:
                    holdings = session.query(Holdings).filter(Holdings.quantity > 0).all()
                
                for h in holdings:
                    current_price = h.avg_price # 시뮬레이션은 현재가 업데이트 필요
                    profit_rate = 0.0 
                    if h.avg_price > 0:
                        # 시뮬레이션에서도 현재가가 업데이트 되어있다면 수익률 계산
                        profit_rate = ((current_price - h.avg_price) / h.avg_price) * 100
                    
                    holdings_data.append({
                        "종목코드": h.item_cd,
                        "종목명": h.item_nm or h.item_cd,
                        "보유수량": h.quantity,
                        "매입가": int(h.avg_price),
                        "현재가": int(current_price),
                        "평가금액": int(current_price * h.quantity),
                        "수익률": profit_rate
                    })
        except Exception as e:
            st.error(f"보유 종목 조회 오류: {e}")

    # 2. 실전/모의 모드: API 조회
    else:
        try:
            settings = settings_manager.settings
            api_mode = "real" if settings.api.kis_trading_account_mode == "real" and account_type == "real_trading" else "mock"
            
            fetcher = KISAPIFetcher(mode=api_mode)
            
            if api_mode == "real":
                acct_no = settings.api.kis_real_account_no
                acct_cd = settings.api.kis_real_account_cd
            else:
                acct_no = settings.api.kis_mock_account_no
                acct_cd = settings.api.kis_mock_account_cd
            
            if acct_no and acct_cd:
                balance = fetcher.get_account_balance(acct_no, acct_cd)
                
                if balance and 'holdings' in balance:
                    for h in balance['holdings']:
                        qty = int(h.get('hldg_qty', 0))
                        if qty > 0:
                            holdings_data.append({
                                "종목코드": h.get('pdno'),
                                "종목명": h.get('prdt_name'),
                                "보유수량": qty,
                                "매입가": int(float(h.get('pchs_avg_pric', 0))),
                                "현재가": int(h.get('prpr', 0)),
                                "평가금액": int(h.get('evlu_amt', 0)),
                                "수익률": float(h.get('evlu_pfls_rt', 0))
                            })
        except Exception as e:
            st.error(f"API 조회 오류: {e}")

    # 그리드 출력
    if holdings_data:
        with st.expander("📋 보유 종목 상세 보기", expanded=True):
            df = pd.DataFrame(holdings_data)
            st.dataframe(
                df,
                width="stretch",
                hide_index=True,
                column_config={
                    "매입가": st.column_config.NumberColumn(format="%d원"),
                    "현재가": st.column_config.NumberColumn(format="%d원"),
                    "평가금액": st.column_config.NumberColumn(format="%d원"),
                    "보유수량": st.column_config.NumberColumn(format="%d주"),
                    "수익률": st.column_config.NumberColumn(format="%.2f%%"),
                }
            )
    else:
        st.info("보유 중인 종목이 없습니다.")


def render_buy_candidates_table(base_date, min_score):
    """매수 후보 종목 테이블"""
    if not base_date:
        return

    try:
        with get_session() as session:
            # 평가 결과와 종목명 조인
            query = session.query(
                EvaluationResult, ItemMst.itms_nm, ItemMst.mrkt_ctg
            ).join(
                ItemMst, EvaluationResult.item_cd == ItemMst.item_cd
            ).filter(
                EvaluationResult.base_date == base_date,
                EvaluationResult.total_score >= min_score
            ).order_by(
                desc(EvaluationResult.total_score)
            ).limit(20) # 상위 20개만 표시
            
            rows = query.all()
            
            data = []
            for res, nm, mkt in rows:
                data.append({
                    "종목코드": res.item_cd,
                    "종목명": nm,
                    "시장": mkt,
                    "총점": res.total_score,
                    # "등급": res.grade,  <-- 제거됨 (DB 컬럼 없음)
                    # "현재가": res.current_price, # <-- 수정됨 (.price -> .current_price)
                    "재무점수": res.sheet_score,
                    "추세점수": res.trend_score,
                    "수급점수": res.buy_score, 
                    "주가점수": res.price_score,
                    "KPI점수": res.kpi_score,
                    "시총점수": res.avls_score,
                    "PER점수": res.per_score,
                    "PBR점수": res.pbr_score,
                })
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(
                    df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="%d원"),
                        "총점": st.column_config.ProgressColumn(
                            format="%.1f",
                            min_value=0,
                            max_value=40,
                        ),
                    }
                )
    except Exception as e:
        st.error(f"매수 후보 조회 오류: {e}")