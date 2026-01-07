"""
데이터수집 페이지
- 기준 날짜 선택
- 데이터 수집 실행 (조건부 제한)
- 수집 데이터 초기화
- 수집 결과 조회 (페이징, 필터링)
- 스케줄 설정
- 실행 로그
"""

import streamlit as st
from datetime import datetime, date, timedelta
import time

from config.settings import get_settings_manager
from config.database import get_session, ItemMst, FinancialSheet, ScheduleLog
from data.dart_collector import DataCollectionService
from scheduler.task_manager import get_scheduler, TaskType
from ui.components import render_log_grid, render_data_grid_with_paging, render_schedule_config, render_log_section


def render_data_collection():
    """데이터수집 페이지 렌더링"""
    st.markdown('<div class="main-header">📥 데이터수집</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    settings = settings_manager.settings
    
    # ========== 안내 문구 (OpenDart 한도 & 보관 기간) ==========
    st.warning("⚠️ **Open DART API 주의**: 하루 사용량이 **10,000건**으로 제한됩니다. 초과 시 서비스가 차단될 수 있습니다.")
    st.info("💡 **KIS Open API**: 당일 데이터는 장 종료 후 제공됩니다.")
    st.info("💡 **데이터 보관 정책**: 효율적인 관리를 위해 수집 데이터는 **최근 1개월치만 보관**되며, 수집 실행 시 1개월 이전 데이터는 자동 삭제됩니다.")
    
    st.divider()

    # ========== 기준 날짜 선택 ==========
    st.markdown("### 📅 기준 날짜")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        base_date = st.date_input(
            "수집 기준일",
            value=date.today(),
            max_value=date.today(),
            key="collection_base_date"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(f"📅 선택된 날짜: **{base_date.strftime('%Y-%m-%d')}**")
    
    st.divider()
    
    # ========== 수집 설정 및 실행 ==========
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ⚙️ 수집 설정")
        
        collection_settings = settings.collection
        
        # 시장 선택
        collect_kospi = st.checkbox(
            "KOSPI",
            value=collection_settings.collect_kospi,
            key="dc_kospi"
        )
        collect_kosdaq = st.checkbox(
            "KOSDAQ",
            value=collection_settings.collect_kosdaq,
            key="dc_kosdaq"
        )
        
        # 수집 모드
        collection_mode = st.radio(
            "수집 모드",
            options=["random_n", "all"],
            format_func=lambda x: f"무작위 N개 (테스트)" if x == "random_n" else "전체 (스케줄 권장)",
            index=0 if collection_settings.collection_mode == "random_n" else 1,
            key="dc_mode",
            horizontal=True
        )
        
        if collection_mode == "random_n":
            random_n = st.number_input(
                "무작위 종목 수 (최대 100개)",
                min_value=1,
                max_value=100,  # 최대 100개 제한
                value=min(collection_settings.random_n_stocks, 100),
                key="dc_random_n"
            )
        else:
            random_n = collection_settings.random_n_stocks
        
        # 설정 저장
        if st.button("💾 설정 저장", key="dc_save_settings"):
            settings_manager.update_collection(
                collect_kospi=collect_kospi,
                collect_kosdaq=collect_kosdaq,
                collection_mode=collection_mode,
                random_n_stocks=random_n
            )
            st.success("✅ 설정이 저장되었습니다.")
    
    with col2:
        st.markdown("### 🚀 실행")
        
        # API 상태 확인
        api_settings = settings.api
        api_ok = True
        
        if not api_settings.krx_api_key:
            st.error("❌ KRX API 키 필요")
            api_ok = False
        if not api_settings.opendart_api_key:
            st.error("❌ OpenDart API 키 필요")
            api_ok = False
            
        # KIS API 상태
        kis_mode = api_settings.kis_api_mode
        if kis_mode == "real":
            if not (api_settings.kis_real_app_key and api_settings.kis_real_app_secret):
                st.warning("⚠️ KIS API (실전) 미설정 - 시세/수급 수집 불가")
        else:
            if not (api_settings.kis_mock_app_key and api_settings.kis_mock_app_secret):
                st.warning("⚠️ KIS API (모의) 미설정 - 시세/수급 수집 불가")
        
        st.caption(f"📡 데이터 수집 API: {'실전투자' if kis_mode == 'real' else '모의투자'}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 실행 버튼 (이어하기 버튼 제거됨)
        if st.button("🚀 데이터 수집 실행", type="primary", width="stretch", key="dc_run", disabled=not api_ok):
            # 실행 조건 체크
            if collection_mode == "all":
                st.error("⛔ 전체 수집은 **자동스케줄 설정**으로만 가능합니다.")
            elif collection_mode == "random_n" and random_n > 100:
                st.error("⛔ 무작위 수집은 **최대 100건**까지만 가능합니다.")
            else:
                run_data_collection(base_date)
        
        if collection_mode == "all":
            st.caption("ℹ️ '전체' 모드는 데이터 양이 많아 스케줄 실행을 권장합니다.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 초기화 버튼
        with st.expander("🗑️ 데이터 초기화"):
            st.warning(f"⚠️ {base_date} 날짜의 모든 수집 데이터가 삭제됩니다!")
            
            if st.button("🗑️ 선택한 날짜 데이터 삭제", type="secondary", key="dc_delete"):
                delete_collection_data(base_date)
    
    st.divider()
    
    # ========== 스케줄 설정 ==========
    render_schedule_config(
        task_type="data_collection",
        schedule_key="dc_schedule",
        default_cron="30 8 * * 1-5"
    )
    
    st.divider()
    
    # ========== 실행 로그 ==========
    render_log_section("data_collection", "📜 최근 실행 로그")
    
    st.divider()
    
    # ========== 수집 결과 데이터 조회 ==========
    st.markdown("### 📊 수집 결과 조회")
    
    render_collection_result_grid(base_date)


def _delete_old_data_before_run(log_callback=None):
    """실행 전 1개월 이전 데이터 삭제 (ItemPrice 제외)"""
    try:
        from config.database import ItemEquity, EvaluationResult, ItemMst
        
        # 1개월 전 날짜 계산
        one_month_ago = date.today() - timedelta(days=30)
        date_str = one_month_ago.strftime('%Y%m%d')
        
        if log_callback:
            log_callback(f"[정리] 1개월 이전 데이터 삭제 중... (기준: {date_str} 이전)")
            
        with get_session() as session:
            # EvaluationResult 삭제
            session.query(EvaluationResult).filter(
                EvaluationResult.base_date < date_str
            ).delete(synchronize_session=False)
            
            # FinancialSheet 삭제
            session.query(FinancialSheet).filter(
                FinancialSheet.base_date < date_str
            ).delete(synchronize_session=False)
            
            # ItemMst 삭제 (오래된 기준일 데이터)
            session.query(ItemMst).filter(
                ItemMst.base_date < date_str
            ).delete(synchronize_session=False)
            
            session.commit()
            
        if log_callback:
            log_callback(f"[정리] 1개월 이전 데이터 삭제 완료")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[정리] 데이터 삭제 중 오류: {e}")


def run_data_collection(base_date: date):
    """데이터 수집 실행 (무작위 N개 전용)"""
    
    log_id = save_schedule_log_start("data_collection", "수동 데이터수집")
    
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
        display_logs = log_messages[-30:]
        log_area.code("\n".join(display_logs), language=None)
    
    try:
        # 1. 이전 데이터 정리
        _delete_old_data_before_run(update_log)
        
        collection_service = DataCollectionService()
        
        status_text.text("데이터 수집 시작...")
        update_log(f"[시작] 데이터 수집 시작 (기준일: {base_date})")
        
        result = collection_service.run_full_collection(
            base_date=base_date,
            collect_source='manual',
            progress_callback=update_progress,
            log_callback=update_log
        )
        
        progress_bar.progress(100)
        
        result_msg = f"종목 {result.get('items_collected', 0)}개, 재무 {result.get('financial_collected', 0)}개 수집"
        
        if result.get('errors'):
            status_text.text(f"⚠️ 수집 완료 (오류 {len(result['errors'])}건)")
            st.warning(f"수집 완료 (오류 {len(result['errors'])}건)")
            save_schedule_log_end(log_id, "success", result_msg + f", 오류 {len(result['errors'])}건")
        else:
            status_text.text("✅ 수집 완료!")
            st.success("데이터 수집이 완료되었습니다.")
            save_schedule_log_end(log_id, "success", result_msg)
        
        _render_result_metrics(result)
        
    except Exception as e:
        progress_bar.progress(100)
        status_text.text(f"❌ 오류 발생")
        st.error(f"데이터 수집 오류: {e}")
        update_log(f"[오류] {e}")
        save_schedule_log_end(log_id, "failed", None, str(e))


def _render_result_metrics(result):
    """수집 결과 요약 메트릭 표시"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("종목 저장", f"{result.get('items_collected', 0)}개")
    with col2:
        st.metric("재무 수집", f"{result.get('financial_collected', 0)}개")
    with col3:
        st.metric("재무 없음", f"{result.get('financial_skipped', 0)}개")
    with col4:
        st.metric("오류", f"{len(result.get('errors', []))}개")


def save_schedule_log_start(task_type: str, schedule_name: str) -> int:
    """실행 로그 시작 기록"""
    try:
        with get_session() as session:
            log = ScheduleLog(
                schedule_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                schedule_name=schedule_name,
                task_type=task_type,
                status="running",
                start_time=datetime.now()
            )
            session.add(log)
            session.flush()
            return log.id
    except Exception as e:
        st.warning(f"로그 기록 오류: {e}")
        return 0


def save_schedule_log_end(log_id: int, status: str, message: str = None, error: str = None):
    """실행 로그 종료 기록"""
    if log_id == 0:
        return
    
    try:
        with get_session() as session:
            log = session.query(ScheduleLog).filter(ScheduleLog.id == log_id).first()
            if log:
                log.status = status
                log.end_time = datetime.now()
                log.message = message
                log.error_message = error
                session.commit()
    except Exception as e:
        pass


def delete_collection_data(base_date: date):
    """선택한 날짜의 수집 데이터 삭제 (ItemPrice 제외 - 1년치 이력 유지)"""
    try:
        from config.database import ItemEquity, EvaluationResult
        
        with get_session() as session:
            # 해당 날짜의 종목 데이터 삭제
            date_str = base_date.strftime('%Y%m%d')
            
            # EvaluationResult 삭제
            deleted_eval = session.query(EvaluationResult).filter(
                EvaluationResult.base_date == date_str
            ).delete()
            
            # FinancialSheet에서 해당 날짜 데이터 삭제
            deleted_financial = session.query(FinancialSheet).filter(
                FinancialSheet.base_date == date_str
            ).delete()
            
            # ItemMst에서 해당 날짜의 종목 코드 조회
            items = session.query(ItemMst.item_cd).filter(
                ItemMst.base_date == date_str
            ).all()
            item_codes = [i[0] for i in items]
            
            deleted_equity = 0
            if item_codes:
                deleted_equity = session.query(ItemEquity).filter(
                    ItemEquity.item_cd.in_(item_codes)
                ).delete(synchronize_session='fetch')
            
            # ItemMst에서 해당 날짜 데이터 삭제
            deleted_items = session.query(ItemMst).filter(
                ItemMst.base_date == date_str
            ).delete()
            
            session.commit()
            
            st.success(f"""
            ✅ 삭제 완료:
            - 종목: {deleted_items}건
            - 재무: {deleted_financial}건  
            - 주식정보: {deleted_equity}건
            - 평가결과: {deleted_eval}건
            
            💡 시세 데이터(ItemPrice)는 1년치 이력을 유지하므로 삭제되지 않습니다.
            """)
            
    except Exception as e:
        st.error(f"삭제 오류: {e}")


def render_collection_result_grid(query_date: date):
    """수집 결과 데이터 그리드 (필터링 기능 포함)"""
    
    # 조회 옵션 - 첫 번째 줄
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        selected_date = st.date_input(
            "조회 날짜",
            value=query_date,
            max_value=date.today(),
            key="dc_query_date"
        )
    
    with col2:
        source_filter = st.selectbox(
            "실행구분",
            options=["ALL", "manual", "auto"],
            format_func=lambda x: {
                "ALL": "전체",
                "manual": "🖐️ 수동",
                "auto": "⚡ 자동"
            }.get(x),
            key="dc_source_filter"
        )
    
    with col3:
        filter_option = st.selectbox(
            "재무데이터",
            options=["all", "with_financial", "without_financial"],
            format_func=lambda x: {
                "all": "전체",
                "with_financial": "✅ 있음",
                "without_financial": "❌ 없음"
            }.get(x),
            key="dc_filter"
        )
    
    with col4:
        market_filter = st.selectbox(
            "시장",
            options=["ALL", "KOSPI", "KOSDAQ"],
            key="dc_market_filter"
        )
    
    with col5:
        search_keyword = st.text_input(
            "종목명 검색",
            placeholder="삼성",
            key="dc_search"
        )
    
    # 데이터 조회
    try:
        with get_session() as session:
            date_str = selected_date.strftime('%Y%m%d')
            
            # 종목 + 재무 데이터 조인 조회
            query = session.query(
                ItemMst.item_cd,
                ItemMst.itms_nm,
                ItemMst.mrkt_ctg,
                ItemMst.sector,
                ItemMst.collect_source,
                FinancialSheet.roe_val,
                FinancialSheet.lblt_rate,
                FinancialSheet.bsop_prfi_inrt,
                FinancialSheet.grs,
                FinancialSheet.eps,
                FinancialSheet.bps
            ).outerjoin(
                FinancialSheet,
                (ItemMst.item_cd == FinancialSheet.item_cd) & 
                (ItemMst.base_date == FinancialSheet.base_date)
            ).filter(
                ItemMst.base_date == date_str
            )
            
            # 실행구분 필터
            if source_filter != "ALL":
                query = query.filter(ItemMst.collect_source == source_filter)
            
            # 시장 필터
            if market_filter != "ALL":
                query = query.filter(ItemMst.mrkt_ctg == market_filter)
            
            # 종목명 검색
            if search_keyword:
                query = query.filter(ItemMst.itms_nm.like(f"%{search_keyword}%"))
            
            results = query.all()
            
            # 결과 데이터 변환
            data = []
            financial_count = 0
            
            for row in results:
                has_financial = row.roe_val is not None or row.lblt_rate is not None
                
                # 필터 적용
                if filter_option == "with_financial" and not has_financial:
                    continue
                if filter_option == "without_financial" and has_financial:
                    continue
                
                if has_financial:
                    financial_count += 1
                
                source_display = "🖐️" if row.collect_source == "manual" else "⚡" if row.collect_source == "auto" else ""
                
                data.append({
                    "구분": source_display,
                    "종목코드": row.item_cd,
                    "종목명": row.itms_nm or "",
                    "시장": row.mrkt_ctg or "",
                    "ROE": f"{row.roe_val:.2f}%" if row.roe_val else "-",
                    "부채비율": f"{row.lblt_rate:.2f}%" if row.lblt_rate else "-",
                    "영업이익률": f"{row.bsop_prfi_inrt:.2f}%" if row.bsop_prfi_inrt else "-",
                    "매출성장률": f"{row.grs:.2f}%" if row.grs else "-",
                    "재무": "✅" if has_financial else ""
                })
            
            if data:
                # 통계 표시
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("조회 결과", f"{len(data)}건")
                with col2:
                    st.metric("재무데이터 있음", f"{financial_count}건")
                with col3:
                    st.metric("재무데이터 없음", f"{len(data) - financial_count}건")
                
                render_data_grid_with_paging(
                    data=data,
                    columns=["구분", "종목코드", "종목명", "시장", "ROE", "부채비율", "영업이익률", "매출성장률", "재무"],
                    page_size=20,
                    key_prefix="dc_result"
                )
            else:
                st.info(f"{selected_date} 날짜의 수집 데이터가 없습니다.")
                
    except Exception as e:
        st.error(f"데이터 조회 오류: {e}")