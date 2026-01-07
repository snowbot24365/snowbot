"""
수동 실행 페이지 UI
- 데이터 수집, 종목 평가, 자동 매매 수동 실행
- 실시간 로그 표시
"""

import streamlit as st
from datetime import datetime
import time

from config.settings import get_settings_manager
from scheduler.task_manager import get_scheduler, TaskType
from data.dart_collector import DataCollectionService


def render_manual_run():
    """수동 실행 페이지 렌더링"""
    st.markdown('<div class="main-header">🔧 수동 실행</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    
    st.info("""
    각 작업을 수동으로 실행할 수 있습니다.
    - **데이터 수집**: KRX에서 종목 목록, OpenDart에서 재무제표를 수집합니다.
    - **종목 평가**: 수집된 데이터를 기반으로 종목을 평가하고 점수를 산출합니다.
    - **자동 매매**: 평가 결과를 바탕으로 매수/매도를 자동 실행합니다.
    """)
    
    # 탭으로 구분
    tab1, tab2, tab3 = st.tabs(["📥 데이터 수집", "📊 종목 평가", "💰 자동 매매"])
    
    # ========== 데이터 수집 탭 ==========
    with tab1:
        st.subheader("📥 데이터 수집")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 수집 설정")
            
            collection_settings = settings_manager.settings.collection
            
            # 시장 선택
            st.markdown("**시장 선택**")
            collect_kospi = st.checkbox(
                "KOSPI",
                value=collection_settings.collect_kospi,
                key="collect_kospi"
            )
            collect_kosdaq = st.checkbox(
                "KOSDAQ",
                value=collection_settings.collect_kosdaq,
                key="collect_kosdaq"
            )
            
            st.divider()
            
            # 수집 범위
            st.markdown("**수집 범위**")
            collection_mode = st.radio(
                "수집 모드",
                options=["random_n", "all"],
                format_func=lambda x: "무작위 N개 (테스트용)" if x == "random_n" else "전체",
                index=0 if collection_settings.collection_mode == "random_n" else 1,
                key="collection_mode"
            )
            
            if collection_mode == "random_n":
                random_n = st.number_input(
                    "무작위 종목 수",
                    min_value=1,
                    max_value=100,
                    value=collection_settings.random_n_stocks,
                    help="전체 종목 중 무작위로 N개를 선택하여 재무제표를 수집합니다.",
                    key="random_n"
                )
                st.caption("💡 전체 수집 전 테스트 목적으로 사용합니다.")
            else:
                random_n = collection_settings.random_n_stocks
                st.warning("⚠️ 전체 수집은 시간이 오래 걸릴 수 있습니다. (약 1~2시간)")
            
            # 설정 저장
            if st.button("💾 설정 저장", key="save_collection"):
                settings_manager.update_collection(
                    collect_kospi=collect_kospi,
                    collect_kosdaq=collect_kosdaq,
                    collection_mode=collection_mode,
                    random_n_stocks=random_n
                )
                st.success("✅ 수집 설정이 저장되었습니다.")
        
        with col2:
            st.markdown("#### 수집 항목")
            st.markdown("""
            **1단계: KRX 종목 목록**
            - KOSPI/KOSDAQ 상장 종목
            - 종목코드, 종목명, 업종
            
            **2단계: OpenDart 재무제표**
            - 전년도 사업보고서 기준
            - ROE, 부채비율, 영업이익률
            """)
            
            # API 키 상태 확인
            st.divider()
            st.markdown("**API 상태**")
            
            api_settings = settings_manager.settings.api
            if api_settings.opendart_api_key:
                st.success("✅ OpenDart API 키 설정됨")
            else:
                st.error("❌ OpenDart API 키 필요")
        
        st.divider()
        
        # 실행 버튼
        if st.button("🚀 데이터 수집 실행", type="primary", key="run_collection", width="stretch"):
            run_data_collection()
    
    # ========== 종목 평가 탭 ==========
    with tab2:
        st.subheader("📊 종목 평가")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 평가 설정")
            
            eval_settings = settings_manager.settings.evaluation
            
            min_score = st.slider(
                "최소 총점 (매수 후보 기준)",
                min_value=10,
                max_value=50,
                value=eval_settings.min_total_score,
                key="min_score"
            )
            
            if st.button("💾 설정 저장", key="save_eval"):
                settings_manager.update_evaluation(min_total_score=min_score)
                st.success("✅ 평가 설정이 저장되었습니다.")
        
        with col2:
            st.markdown("#### 평가 항목")
            st.markdown("""
            - 📈 재무 점수 (매출성장, ROE, 부채비율)
            - 📊 추세 점수 (이동평균선 배열)
            - 💰 가격 점수 (52주 고저 대비)
            - 🏦 수급 점수 (외국인/기관 매수)
            - 📉 밸류에이션 (PER, PBR)
            - 🔧 기술지표 (RSI, OBV)
            """)
        
        st.divider()
        
        if st.button("🚀 종목 평가 실행", type="primary", key="run_evaluation", width="stretch"):
            run_task_with_progress(TaskType.EVALUATION, "종목 평가")
    
    # ========== 자동 매매 탭 ==========
    with tab3:
        st.subheader("💰 자동 매매")
        
        # 현재 모드 표시
        mode = settings_manager.settings.execution_mode
        if mode == "simulation":
            st.success("🎮 **시뮬레이션 모드** - 가상 계좌로 테스트합니다.")
        else:
            st.error("💰 **실거래 모드** - 실제 자금으로 거래됩니다!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 매매 설정")
            
            trading_settings = settings_manager.settings.trading
            
            buy_enabled = st.checkbox(
                "매수 활성화",
                value=trading_settings.buy_enabled,
                key="buy_enabled"
            )
            
            st.write(f"- 익절선: **+{trading_settings.sell_up_rate}%**")
            st.write(f"- 손절선: **{trading_settings.sell_down_rate}%**")
            st.write(f"- 최대 보유: **{trading_settings.limit_count}종목**")
            
            if st.button("💾 설정 저장", key="save_trading"):
                settings_manager.update_trading(buy_enabled=buy_enabled)
                st.success("✅ 매매 설정이 저장되었습니다.")
        
        with col2:
            st.markdown("#### 실행 내용")
            st.markdown("""
            **매도 체크:**
            - 익절선 도달 여부
            - 손절선 도달 여부
            - 트레일링 스탑 조건
            
            **매수 체크:**
            - 매수 후보 스코어
            - 잔고 및 보유 한도
            - 매수 조건 충족 여부
            """)
        
        st.divider()
        
        if st.button("🚀 자동 매매 실행", type="primary", key="run_trading", width="stretch"):
            if mode == "real_trading":
                st.warning("⚠️ **실거래 모드**입니다. 실제 주문이 실행됩니다!")
                confirm = st.checkbox("실거래 실행에 동의합니다.", key="confirm_real_trade")
                if confirm:
                    if st.button("✅ 예, 실행합니다", key="confirm_trading"):
                        run_task_with_progress(TaskType.AUTO_TRADE, "자동 매매")
            else:
                run_task_with_progress(TaskType.AUTO_TRADE, "자동 매매")
    
    st.divider()
    
    # ========== 실행 로그 ==========
    st.subheader("📜 최근 실행 로그")
    
    try:
        scheduler = get_scheduler()
        logs = scheduler.get_schedule_logs(limit=20)
        
        if logs:
            log_data = []
            for log in logs:
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'running': '🔄'
                }.get(log['status'], '⚪')
                
                log_data.append({
                    "상태": f"{status_emoji} {log['status']}",
                    "작업": log['task_type'],
                    "이름": log['schedule_name'],
                    "시작": log['start_time'][:19] if log['start_time'] else "",
                    "종료": log['end_time'][:19] if log['end_time'] else "",
                    "메시지": log['message'] or log['error_message'] or ""
                })
            
            st.dataframe(log_data, width="stretch", hide_index=True)
        else:
            st.info("실행 로그가 없습니다.")
            
    except Exception as e:
        st.warning(f"로그 조회 오류: {e}")
    
    # 새로고침 버튼
    if st.button("🔄 새로고침"):
        st.rerun()


def run_data_collection():
    """데이터 수집 실행 (실시간 로그 표시)"""
    
    # 진행 상태 영역
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 로그 출력 영역
    log_container = st.container()
    log_area = log_container.empty()
    log_messages = []
    
    def update_progress(current, total, message):
        """진행률 업데이트"""
        progress = int((current / total) * 100) if total > 0 else 0
        progress_bar.progress(progress)
        status_text.text(f"[{progress}%] {message}")
    
    def update_log(message):
        """로그 업데이트"""
        log_messages.append(message)
        # 최근 30개만 표시
        display_logs = log_messages[-30:]
        log_area.text_area(
            "실행 로그",
            value="\n".join(display_logs),
            height=400,
            key=f"log_{len(log_messages)}"
        )
    
    try:
        # 데이터 수집 서비스 초기화
        collection_service = DataCollectionService()
        
        status_text.text("데이터 수집 시작...")
        update_log("[시작] 데이터 수집을 시작합니다.")
        
        # 수집 실행
        result = collection_service.run_full_collection(
            progress_callback=update_progress,
            log_callback=update_log
        )
        
        # 완료
        progress_bar.progress(100)
        
        if result.get('errors'):
            status_text.text(f"⚠️ 수집 완료 (오류 {len(result['errors'])}건)")
            st.warning(f"수집이 완료되었지만 {len(result['errors'])}건의 오류가 발생했습니다.")
        else:
            status_text.text("✅ 수집 완료!")
            st.success("데이터 수집이 성공적으로 완료되었습니다.")
        
        # 결과 요약
        st.markdown("### 📊 수집 결과")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("종목 저장", f"{result.get('items_collected', 0)}개")
        with col2:
            st.metric("재무 수집", f"{result.get('financial_collected', 0)}개")
        with col3:
            st.metric("재무 없음", f"{result.get('financial_skipped', 0)}개")
        with col4:
            st.metric("오류", f"{len(result.get('errors', []))}개")
        
    except Exception as e:
        progress_bar.progress(100)
        status_text.text(f"❌ 오류 발생")
        st.error(f"데이터 수집 오류: {e}")
        update_log(f"[오류] {e}")


def run_task_with_progress(task_type: str, task_name: str):
    """진행 상황과 함께 작업 실행"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        scheduler = get_scheduler()
        
        status_text.text(f"{task_name} 시작...")
        progress_bar.progress(10)
        
        # 작업 실행
        result = scheduler.run_now(task_type)
        
        progress_bar.progress(100)
        
        if result['success']:
            status_text.text(f"✅ {result['message']}")
            st.success(f"{task_name}이(가) 완료되었습니다.")
        else:
            status_text.text(f"❌ {result['message']}")
            st.error(f"{task_name} 실패: {result['message']}")
            
    except Exception as e:
        progress_bar.progress(100)
        status_text.text(f"❌ 오류 발생")
        st.error(f"{task_name} 오류: {e}")
    
    finally:
        time.sleep(1)
