"""
종목평가 페이지
- 기준 날짜 선택 (최신 수집일 자동 감지 및 분리 적용)
- 종목 평가 실행
- 평가 결과 초기화
- 평가 결과 조회 (페이징)
- 스케줄 설정
- 실행 로그
"""

import streamlit as st
from datetime import datetime, date
import time
from sqlalchemy import func # Max 집계 함수 사용을 위해 추가

from config.settings import get_settings_manager
from config.database import get_session, EvaluationResult, ItemMst
from scheduler.task_manager import get_scheduler, TaskType
from ui.components import render_log_grid, render_data_grid_with_paging, render_schedule_config, render_log_section


def render_evaluation():
    """종목평가 페이지 렌더링"""
    st.markdown('<div class="main-header">📊 종목평가</div>', unsafe_allow_html=True)
    
    settings_manager = get_settings_manager()
    settings = settings_manager.settings
    
    # ========== [핵심 로직] 최신 데이터 정보 자동 조회 ==========
    # DB에서 가장 최근 수집된 날짜와 개수를 먼저 확인합니다.
    latest_date_str, latest_count = get_latest_data_info()
    
    # ========== 1. 기준 날짜 선택 (결과가 저장될 날짜) ==========
    st.markdown("### 📅 기준 날짜")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # 평가 기준일은 사용자가 자유롭게 선택 (기본값: 오늘)
        # 이 날짜로 EvaluationResult 테이블에 저장됩니다.
        target_base_date = st.date_input(
            "평가 기준일 (결과 저장일)",
            value=date.today(),
            max_value=date.today(),
            key="eval_base_date"
        )
    
    # ========== 2. 데이터 상태 표시 ==========
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if latest_date_str and latest_count > 0:
            # 보기 좋게 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
            formatted_data_date = f"{latest_date_str[:4]}-{latest_date_str[4:6]}-{latest_date_str[6:]}"
            
            # 기준일과 데이터 날짜가 다를 경우 명확히 안내
            if target_base_date.strftime('%Y%m%d') != latest_date_str:
                st.info(f"ℹ️ **데이터 출처: {formatted_data_date}** ({latest_count:,}개)")
            else:
                st.success(f"✅ 최신 데이터 기준 ({latest_count:,}개)")
        else:
            st.warning("⚠️ 수집된 데이터가 없습니다.")

    st.divider()
    
    # ========== 평가 설정 및 실행 ==========
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ⚙️ 평가 설정")
        
        eval_settings = settings.evaluation
        
        min_score = st.slider(
            "최소 총점 (매수 후보 기준)",
            min_value=10,
            max_value=50,
            value=eval_settings.min_total_score,
            key="eval_min_score"
        )
        
        st.markdown("**지표별 가중치:**")
        
        # 가중치 표시 (2열 4행)
        weight_data = [
            ("재무", eval_settings.weight_sheet),
            ("모멘텀", eval_settings.weight_trend),
            ("주가", eval_settings.weight_price),
            ("KPI", eval_settings.weight_kpi),
            ("수급", eval_settings.weight_buy),
            ("시총", eval_settings.weight_avls),
            ("PER", eval_settings.weight_per),
            ("PBR", eval_settings.weight_pbr),
        ]
        
        col_a, col_b = st.columns(2)
        with col_a:
            for name, weight in weight_data[:4]:
                st.caption(f"• {name}: {weight:.1f}")
        with col_b:
            for name, weight in weight_data[4:]:
                st.caption(f"• {name}: {weight:.1f}")
        
        st.caption("💡 가중치는 설정 > 매매설정에서 변경 가능합니다.")
    
    with col2:
        st.markdown("### 🚀 실행")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 실행 버튼
        if st.button("🚀 종목 평가 실행", type="primary", width="stretch", key="eval_run"):
            # 데이터가 존재하는지 확인
            if latest_date_str and latest_count > 0:
                # [핵심] 기준일(target_base_date)과 데이터일(latest_date_str)을 분리해서 전달
                run_evaluation(
                    base_date=target_base_date,   # 결과 저장용 (오늘)
                    data_date_str=latest_date_str, # 데이터 조회용 (최근일)
                    min_score=min_score
                )
            else:
                st.error("평가할 기초 데이터가 DB에 없습니다. [데이터 수집]을 먼저 수행해주세요.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 초기화 버튼
        with st.expander("🗑️ 평가 결과 초기화"):
            st.warning(f"⚠️ {target_base_date} 날짜의 모든 평가 결과가 삭제됩니다!")
            
            if st.button("🗑️ 선택한 날짜 평가 결과 삭제", type="secondary", key="eval_delete"):
                delete_evaluation_data(target_base_date)
    
    st.divider()
    
    # ========== 스케줄 설정 ==========
    render_schedule_config(
        task_type="evaluation",
        schedule_key="eval_schedule",
        default_cron="50 8 * * 1-5"
    )
    
    st.divider()
    
    # ========== 실행 로그 ==========
    render_log_section("evaluation", "📜 최근 실행 로그")
    
    st.divider()
    
    # ========== 평가 결과 데이터 조회 ==========
    st.markdown("### 📊 평가 결과 조회")
    
    # 조회 날짜 기본값도 사용자가 보고 있던 날짜로 연동
    render_evaluation_result_grid(target_base_date)


def get_latest_data_info() -> tuple[str, int]:
    """
    DB에 저장된 가장 최근 데이터의 날짜와 개수를 조회
    Returns:
        (latest_date_str, count): ('20250107', 2500) 또는 (None, 0)
    """
    try:
        with get_session() as session:
            # 1. 가장 최근 날짜(base_date의 최대값) 조회
            latest_date = session.query(func.max(ItemMst.base_date)).scalar()
            
            if not latest_date:
                return None, 0
            
            # 2. 해당 날짜의 데이터 개수 조회
            count = session.query(ItemMst).filter(
                ItemMst.base_date == latest_date
            ).count()
            
            return latest_date, count
            
    except Exception as e:
        # 로그는 상위나 별도 로거에서 처리
        return None, 0


def run_evaluation(base_date: date, data_date_str: str, min_score: int):
    """
    종목 평가 실행 래퍼 함수
    :param base_date: 평가 결과가 저장될 기준 날짜 (EvaluationResult.base_date)
    :param data_date_str: 실제 데이터를 조회할 날짜 (ItemMst.base_date)
    """
    from data.evaluator import EvaluationService
    from config.database import ScheduleLog
    
    # 실행 로그 기록 시작 (기준일로 기록)
    log_id = 0
    try:
        with get_session() as session:
            log = ScheduleLog(
                schedule_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                schedule_name="수동 종목평가",
                task_type="evaluation",
                status="running",
                start_time=datetime.now(),
                message=f"기준일: {base_date}, 데이터일: {data_date_str}"
            )
            session.add(log)
            session.flush()
            log_id = log.id
    except Exception as e:
        st.warning(f"로그 기록 오류: {e}")
    
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
        # 최신 30개 로그만 표시
        display_logs = log_messages[-30:]
        log_area.code("\n".join(display_logs), language=None)
    
    try:
        eval_service = EvaluationService()
        
        status_text.text("종목 평가 시작...")
        update_log(f"[설정] 평가 기준일: {base_date}")
        update_log(f"[설정] 데이터 소스: {data_date_str}")
        
        # [중요] EvaluationService 호출 시 두 개의 날짜를 전달
        # EvaluationService.run_evaluation 메서드가 (base_date, target_data_date) 인자를 받도록 수정되어 있어야 함
        result = eval_service.run_evaluation(
            base_date=base_date,            # 결과 저장용
            target_data_date=data_date_str, # 데이터 조회용
            progress_callback=update_progress,
            log_callback=update_log
        )
        
        progress_bar.progress(100)
        
        result_msg = f"평가 {result.get('total_evaluated', 0)}건, 매수후보 {result.get('buy_candidates', 0)}건"
        
        if result.get('errors'):
            status_text.text(f"⚠️ 평가 완료 (오류 {len(result['errors'])}건)")
            # 로그 저장 (성공했으나 오류 포함)
            if log_id:
                try:
                    with get_session() as session:
                        log = session.query(ScheduleLog).filter(ScheduleLog.id == log_id).first()
                        if log:
                            log.status = "success"
                            log.end_time = datetime.now()
                            log.message = result_msg + f", 오류 {len(result['errors'])}건"
                            session.commit()
                except: pass
        else:
            status_text.text("✅ 평가 완료!")
            st.success(f"평가 완료! (기준일: {base_date}, 사용데이터: {data_date_str})")
            # 로그 저장 (완전 성공)
            if log_id:
                try:
                    with get_session() as session:
                        log = session.query(ScheduleLog).filter(ScheduleLog.id == log_id).first()
                        if log:
                            log.status = "success"
                            log.end_time = datetime.now()
                            log.message = result_msg
                            session.commit()
                except: pass
        
        # 결과 요약 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("평가 종목", f"{result.get('total_evaluated', 0)}개")
        with col2:
            st.metric("매수 후보", f"{result.get('buy_candidates', 0)}개")
        with col3:
            st.metric("오류", f"{len(result.get('errors', []))}개")
        
    except Exception as e:
        progress_bar.progress(100)
        status_text.text(f"❌ 오류 발생")
        st.error(f"종목 평가 오류: {e}")
        update_log(f"[Critical Error] {e}")
        
        # 실패 로그 저장
        if log_id:
            try:
                with get_session() as session:
                    log = session.query(ScheduleLog).filter(ScheduleLog.id == log_id).first()
                    if log:
                        log.status = "failed"
                        log.end_time = datetime.now()
                        log.error_message = str(e)
                        session.commit()
            except: pass


def delete_evaluation_data(base_date: date):
    """선택한 날짜의 평가 결과 삭제"""
    try:
        with get_session() as session:
            date_str = base_date.strftime('%Y%m%d')
            
            deleted = session.query(EvaluationResult).filter(
                EvaluationResult.base_date == date_str
            ).delete()
            
            session.commit()
            
            st.success(f"✅ 삭제 완료: {deleted}건")
            
    except Exception as e:
        st.error(f"삭제 오류: {e}")


def render_evaluation_result_grid(query_date: date):
    """평가 결과 데이터 그리드 (8가지 점수 체계)"""
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        selected_date = st.date_input(
            "조회 날짜",
            value=query_date,
            max_value=date.today(),
            key="eval_query_date"
        )
    
    with col2:
        show_candidates_only = st.checkbox("매수 후보만 보기", key="eval_candidates_only")
    
    # 데이터 조회
    try:
        with get_session() as session:
            date_str = selected_date.strftime('%Y%m%d')
            
            query = session.query(EvaluationResult).filter(
                EvaluationResult.base_date == date_str
            ).order_by(EvaluationResult.total_score.desc()).all()
            
            data = []
            candidates_count = 0
            
            for row in query:
                is_candidate = row.is_buy_candidate
                if is_candidate:
                    candidates_count += 1
                
                # 필터 적용
                if show_candidates_only and not is_candidate:
                    continue
                
                data.append({
                    "종목코드": row.item_cd,
                    "종목명": row.item_nm or "",
                    "총점": row.total_score or 0,
                    "재무": row.sheet_score or 0,
                    "모멘텀": row.trend_score or 0,
                    "주가": row.price_score or 0,
                    "KPI": row.kpi_score or 0,
                    "수급": row.buy_score or 0,
                    "시총": row.avls_score or 0,
                    "PER": row.per_score or 0,
                    "PBR": row.pbr_score or 0,
                    "매수": "✅" if is_candidate else ""
                })
            
            if data:
                # 통계 표시
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("조회 결과", f"{len(query)}건")
                with col2:
                    st.metric("매수 후보", f"{candidates_count}건")
                with col3:
                    avg_score = sum(d["총점"] for d in data) / len(data) if data else 0
                    st.metric("평균 점수", f"{avg_score:.1f}점")
                
                render_data_grid_with_paging(
                    data=data,
                    columns=["종목코드", "종목명", "총점", "재무", "모멘텀", "주가", "KPI", "수급", "시총", "PER", "PBR", "매수"],
                    page_size=20,
                    key_prefix="eval_result"
                )
            else:
                st.info(f"{selected_date} 날짜의 평가 결과가 없습니다.")
                
    except Exception as e:
        st.error(f"데이터 조회 오류: {e}")