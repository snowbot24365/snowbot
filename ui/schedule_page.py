"""
스케줄 관리 및 모니터링 페이지 UI
- 스케줄러 상태 및 다음 실행 시간 확인 (모니터링)
- 스케줄 추가/수정/삭제
- 강제 실행 테스트
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

from config.settings import get_settings_manager, ScheduleItem
from scheduler.task_manager import get_scheduler, TaskType


# 1. [수정] 일반 작업용 프리셋 (수집/평가용 - 장 마감 후 위주)
DEFAULT_PRESETS = {
    "매일 오후 4시 (장 마감 직후)": "0 16 * * *",
    "매일 오후 6시 (데이터 안정)": "0 18 * * *",
    "매일 밤 11시 (야간 작업)": "0 23 * * *",
    "매일 새벽 2시 (서버 부하 ↓)": "0 2 * * *",
    "주말(토) 오전 10시": "0 10 * * 6",
    "직접 입력": ""
}

# 2. [수정] 자동 매매 & 시세 확인용 프리셋 (평일 09:00 ~ 15:59 동작)
AUTO_TRADE_PRESETS = {
    "1분마다 (장중)": "*/1 9-15 * * 1-5",
    "5분마다 (장중)": "*/5 9-15 * * 1-5",
    "10분마다 (장중)": "*/10 9-15 * * 1-5",
    "20분마다 (장중)": "*/20 9-15 * * 1-5",
    "30분마다 (장중)": "*/30 9-15 * * 1-5",
    "1시간마다 (장중)": "0 9-15 * * 1-5",
    "직접 입력": ""
}


def render_schedule():
    """스케줄 관리 페이지 렌더링"""
    st.subheader("스케줄 관리")
    
    scheduler_service = get_scheduler()
    apscheduler = scheduler_service.scheduler
    
    # 상단 상태 표시줄
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        is_running = scheduler_service.is_running()
        status_text = "🟢 실행 중" if is_running else "🔴 중지됨 (일시정지)"
        st.markdown(f"**상태:** {status_text}")
        
    with col2:
        if apscheduler.timezone:
            now = datetime.now(apscheduler.timezone)
            st.markdown(f"**현재 시간:** {now.strftime('%H:%M:%S')} (KST)")
        
    with col3:
        if is_running:
            if st.button("중지", type="secondary", key="stop_scheduler"):
                scheduler_service.stop()
                st.rerun()
        else:
            if st.button("시작", type="primary", key="start_scheduler"):
                scheduler_service.start()
                st.rerun()
    
    st.divider()
    
    # 탭 구성
    tab_monitor, tab_list, tab_add, tab_log = st.tabs(["🔍 모니터링", "📋 스케줄 목록", "➕ 스케줄 추가", "📜 실행 로그"])
    
    # ========== [탭 1] 모니터링 ==========
    with tab_monitor:
        st.subheader("실행 예정 작업 (APScheduler)")
        
        jobs = apscheduler.get_jobs()
        
        if jobs:
            job_data = []
            for job in jobs:
                next_run = job.next_run_time
                if not is_running:
                    next_run_str = "⏸️ 대기중 (스케줄러 중지됨)"
                else:
                    next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else "⏸️ 일시정지"
                
                job_name = job.args[1] if len(job.args) > 1 else job.name
                
                job_data.append({
                    "작업명": job_name,
                    "다음 실행 시간": next_run_str,
                    "트리거": str(job.trigger),
                    "ID": job.id
                })
            
            df = pd.DataFrame(job_data)
            st.dataframe(
                df, 
                width="stretch", 
                hide_index=True,
                column_config={
                    "다음 실행 시간": st.column_config.TextColumn("다음 실행 시간", help="이 시간에 작업이 실행됩니다.")
                }
            )
            
            if st.button("🔄 상태 새로고침", key="refresh_monitor"):
                st.rerun()
        else:
            st.warning("현재 예약된 작업이 없습니다. '스케줄 추가' 탭에서 작업을 등록해주세요.")
            
        st.markdown("---")
        
        # 강제 실행 테스트
        with st.expander("🛠️ 강제 실행 테스트 (디버깅용)"):
            st.info("설정된 시간까지 기다리지 않고 로직을 즉시 실행합니다.")
            
            col_test1, col_test2 = st.columns(2)
            with col_test1:
                if st.button("🚀 데이터 수집 즉시 실행"):
                    scheduler_service.execute_task(TaskType.DATA_COLLECTION, "[수동] 즉시 실행")
                    st.success("데이터 수집 작업이 시작되었습니다.")
            
            with col_test2:
                if st.button("🚀 종목 평가 즉시 실행"):
                    scheduler_service.execute_task(TaskType.EVALUATION, "[수동] 즉시 실행")
                    st.success("종목 평가 작업이 시작되었습니다.")
            
            if st.button("🚀 자동 매매 즉시 실행"):
                scheduler_service.execute_task(TaskType.AUTO_TRADE, "[수동] 즉시 실행")
                st.success("자동 매매 작업이 시작되었습니다.")

    # ========== [탭 2] 스케줄 목록 ==========
    with tab_list:
        st.subheader("등록된 스케줄 설정")
        
        schedules = scheduler_service.get_schedules()
        
        if schedules:
            for schedule in schedules:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        status_emoji = "✅" if schedule.enabled else "⏸️"
                        st.markdown(f"**{status_emoji} {schedule.name}**")
                        st.caption(f"Cron: `{schedule.cron_expression}`")
                    
                    with col2:
                        task_names = {
                            TaskType.DATA_COLLECTION: "📥 데이터 수집",
                            TaskType.EVALUATION: "📊 종목 평가",
                            TaskType.AUTO_TRADE: "💰 자동 매매"
                        }
                        st.write(task_names.get(schedule.task_type, schedule.task_type))
                    
                    with col3:
                        job = apscheduler.get_job(str(schedule.id))
                        if job and job.next_run_time:
                            st.caption(f"예정: {job.next_run_time.strftime('%H:%M:%S')}")
                        else:
                            st.caption("-")
                    
                    with col4:
                        if st.button("🗑️ 삭제", key=f"delete_{schedule.id}", type="secondary"):
                            scheduler_service.delete_schedule(schedule.id)
                            st.success("삭제되었습니다.")
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("등록된 스케줄이 없습니다.")
    
    # ========== [탭 3] 스케줄 추가 ==========
    with tab_add:
        st.subheader("새 스케줄 추가")
        
        name = st.text_input("스케줄 이름", placeholder="예: 자동 매매 (1분 간격)", key="add_name")
        
        task_type = st.selectbox(
            "작업 유형",
            options=[
                TaskType.DATA_COLLECTION,
                TaskType.EVALUATION,
                TaskType.AUTO_TRADE
            ],
            format_func=lambda x: {
                TaskType.DATA_COLLECTION: "📥 데이터 수집",
                TaskType.EVALUATION: "📊 종목 평가",
                TaskType.AUTO_TRADE: "💰 자동 매매"
            }.get(x, x),
            key="add_task_type"
        )
        
        st.markdown("#### 실행 시간 설정")
        
        if task_type in [TaskType.AUTO_TRADE]:
            current_presets = AUTO_TRADE_PRESETS
            st.caption("ℹ️ **자동 매매 및 가격 업데이트는 평일 09:00 ~ 15:59에만 동작하도록 설정됩니다.**")
        else:
            current_presets = DEFAULT_PRESETS
            st.caption("ℹ️ **데이터 수집은 장 마감 후(16:00 이후) 실행을 권장합니다.**")
            
        preset = st.selectbox("프리셋 선택", options=list(current_presets.keys()), key="add_preset")
        
        if preset == "직접 입력":
            # 기본값 설정: 자동매매면 분단위, 아니면 16시
            default_cron = "*/5 9-15 * * 1-5" if task_type in [TaskType.AUTO_TRADE] else "0 16 * * *"
            cron_expression = st.text_input("Cron 표현식", value=default_cron, key="add_cron")
        else:
            cron_expression = current_presets[preset]
            st.info(f"Cron 표현식: `{cron_expression}`")
        
        enabled = st.checkbox("활성화", value=True, key="add_enabled")
        
        if st.button("스케줄 추가", type="primary", key="btn_add_schedule"):
            if not name:
                st.error("스케줄 이름을 입력해주세요.")
            elif not cron_expression:
                st.error("Cron 표현식을 입력해주세요.")
            else:
                try:
                    scheduler_service.add_schedule(
                        name=name, task_type=task_type, 
                        cron_expression=cron_expression, enabled=enabled
                    )
                    st.success(f"'{name}' 스케줄이 추가되었습니다.")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"추가 오류: {e}")
    
    # ========== [탭 4] 실행 로그 ==========
    with tab_log:
        st.subheader("최근 실행 로그")
        
        # 레이아웃을 3개 컬럼으로 분할 (비율 2:1:1)
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # 1. 스케줄 타입 필터 추가
            # 실제 DB에 저장되는 타입 코드와 매핑하거나, 로그에 저장된 'type' 컬럼 값을 사용해야 합니다.
            type_options = ["전체", "매매(auto_trade)", "수집(data_collection)", "평가(evaluation)"]
            selected_type_label = st.selectbox("스케줄 타입", options=type_options, index=0)
            
            # 라벨에서 실제 검색어 추출 (예: "매매(TRADING)" -> "TRADING")
            # "전체"인 경우 None으로 설정하여 필터링 해제
            if "전체" in selected_type_label:
                search_type = None
            else:
                # 괄호 안의 영문 코드를 추출하거나, 한글명을 그대로 사용 (DB 저장 방식에 따름)
                search_type = selected_type_label.split('(')[-1].replace(')', '') 

        with col2:
            log_limit = st.selectbox("표시 개수", options=[20, 50, 100], index=0)
            
        with col3:
            # 버튼 높이 정렬을 위한 공백 (선택 사항)
            st.write("") 
            if st.button("🔄 로그 새로고침", width="stretch"):
                st.rerun()
        
        # 2. 서비스 호출 시 필터 조건 전달
        logs = scheduler_service.get_schedule_logs(limit=log_limit, type_filter=search_type)
        
        if logs:
            log_data = []
            for log in logs:
                status_emoji = {'success': '✅', 'failed': '❌', 'running': '🔄'}.get(log.get('status'), '⚪')
                
                log_data.append({
                    "상태": f"{status_emoji} {log.get('status')}",
                    "타입": log.get('task_type', '-'),  # 타입 컬럼 추가 (데이터에 있다면)
                    "작업명": log.get('schedule_name'),
                    "시작 시간": log.get('start_time'),
                    "종료 시간": log.get('end_time'),
                    "메시지": log.get('message') or log.get('error_message') or ""
                })
            
            # DataFrame 표시
            df_logs = pd.DataFrame(log_data)
            st.dataframe(df_logs, width="stretch", hide_index=True)
        else:
            st.info("조건에 맞는 로그가 없습니다.")