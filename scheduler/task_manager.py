import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.base import STATE_RUNNING, STATE_PAUSED, STATE_STOPPED
import pytz

from config.database import get_session, ScheduleLog, ScheduleItem
from data.dart_collector import DataCollectionService
from trading.strategy import TradingStrategy
from trading.auto_trader import AutoTrader 

logger = logging.getLogger(__name__)

class TaskType:
    DATA_COLLECTION = "data_collection"
    EVALUATION = "evaluation"
    AUTO_TRADE = "auto_trade"
    SYSTEM = "system"  # 시스템 로그용 (필요시 사용)

class SchedulerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        
        # 서울 시간대(KST) 설정
        kst = pytz.timezone('Asia/Seoul')
        
        executors = {
            'default': ThreadPoolExecutor(10)
        }
        
        self.scheduler = BackgroundScheduler(
            timezone=kst, 
            executors=executors
        )
        
        # 초기 시작
        self.scheduler.start()
        self._initialized = True
        
        logger.info(f"스케줄러 서비스 시작됨 (현재시간: {datetime.now(kst)})")
        
        self._load_schedules_from_db()

    def is_running(self):
        """스케줄러가 실행 중인지 확인"""
        return self.scheduler.state == STATE_RUNNING

    def start(self):
        """스케줄러 시작 (일시정지 해제)"""
        if self.scheduler.state == STATE_PAUSED:
            self.scheduler.resume()
            logger.info("스케줄러 재개됨")
        elif self.scheduler.state == STATE_STOPPED:
            self.scheduler.start()
            logger.info("스케줄러 시작됨")

    def stop(self):
        """스케줄러 중지 (일시정지)"""
        if self.scheduler.state == STATE_RUNNING:
            self.scheduler.pause()
            logger.info("스케줄러 일시정지됨")

    def add_schedule(self, name: str, task_type: str, cron_expression: str, enabled: bool = True):
        try:
            with get_session() as session:
                new_schedule = ScheduleItem(
                    name=name,
                    task_type=task_type,
                    cron_expression=cron_expression,
                    enabled=enabled,
                    created_at=datetime.now()
                )
                session.add(new_schedule)
                session.commit()
                
                self._add_job_to_scheduler(new_schedule)
                logger.info(f"스케줄 추가 완료: {name}")
                
        except Exception as e:
            logger.error(f"스케줄 추가 실패: {e}")
            raise

    def delete_schedule(self, schedule_id: int):
        try:
            with get_session() as session:
                schedule = session.query(ScheduleItem).filter(ScheduleItem.id == schedule_id).first()
                if schedule:
                    if self.scheduler.get_job(str(schedule_id)):
                        self.scheduler.remove_job(str(schedule_id))
                    
                    session.delete(schedule)
                    session.commit()
                    logger.info(f"스케줄 삭제 완료: ID {schedule_id}")
        except Exception as e:
            logger.error(f"스케줄 삭제 실패: {e}")

    def get_schedules(self):
        try:
            with get_session() as session:
                session.expire_on_commit = False
                return session.query(ScheduleItem).all()
        except Exception as e:
            logger.error(f"스케줄 조회 실패: {e}")
            return []
    
    def get_schedule_logs(self, limit=20, type_filter: str = None):
        """
        실행 로그 조회
        :param limit: 조회할 개수
        :param type_filter: 필터링할 작업 타입 (UI의 TRADING, COLLECT 등과 매핑)
        """
        try:
            with get_session() as session:
                query = session.query(ScheduleLog)

                # 타입 필터링 로직 추가
                if type_filter and type_filter != "전체":
                    # UI에서 넘어오는 값(TRADING 등)을 DB 값(auto_trade 등)으로 매핑
                    type_mapping = {
                        "TRADING": TaskType.AUTO_TRADE,
                        "COLLECT": TaskType.DATA_COLLECTION,
                        "ANALYSIS": TaskType.EVALUATION,
                        "SYSTEM": TaskType.SYSTEM
                    }
                    # 매핑된 값이 있으면 사용, 없으면 입력값 그대로 검색
                    db_type = type_mapping.get(type_filter, type_filter)
                    query = query.filter(ScheduleLog.task_type == db_type)

                logs = query.order_by(ScheduleLog.start_time.desc()).limit(limit).all()
                
                return [
                    {
                        'status': log.status,
                        'schedule_name': log.schedule_name,
                        'task_type': log.task_type, # UI 표시를 위해 함께 반환
                        'start_time': log.start_time.strftime('%Y-%m-%d %H:%M:%S') if log.start_time else None,
                        'end_time': log.end_time.strftime('%H:%M:%S') if log.end_time else None,
                        'message': log.message,
                        'error_message': log.error_message
                    }
                    for log in logs
                ]
        except Exception as e:
            logger.error(f"로그 조회 실패: {e}")
            return []

    def _load_schedules_from_db(self):
        try:
            with get_session() as session:
                schedules = session.query(ScheduleItem).filter(ScheduleItem.enabled == True).all()
                for item in schedules:
                    self._add_job_to_scheduler(item)
            logger.info(f"초기 스케줄 로드 완료: {len(schedules)}건")
        except Exception as e:
            logger.error(f"스케줄 로드 실패: {e}")

    def _add_job_to_scheduler(self, item: ScheduleItem):
        try:
            trigger = CronTrigger.from_crontab(item.cron_expression, timezone='Asia/Seoul')
            
            self.scheduler.add_job(
                func=self.execute_task,
                trigger=trigger,
                args=[item.task_type, item.name],
                id=str(item.id),
                replace_existing=True,
                misfire_grace_time=3600
            )
            logger.info(f"스케줄 등록: {item.name} ({item.cron_expression})")
        except Exception as e:
            logger.error(f"스케줄 등록 오류 ({item.name}): {e}")

    def execute_task(self, task_type: str, schedule_name: str):
        logger.info(f"===== [{schedule_name}] 작업 시작 (Type: {task_type}) =====")
        
        log_id = self._log_start(task_type, schedule_name)
        
        try:
            result_msg = ""
            
            if task_type == TaskType.DATA_COLLECTION:
                service = DataCollectionService()
                def log_wrapper(msg):
                    logger.info(f"[DataCollection] {msg}")

                result = service.run_incremental_collection(
                    collect_source="auto", 
                    log_callback=log_wrapper
                )
                result_msg = (
                    f"종목:{result.get('items_collected',0)}, "
                    f"재무:{result.get('financial_collected',0)}, "
                    f"시세:{result.get('kis_collected',0)}, "
                    f"오류:{len(result.get('errors',[]))}"
                )
                if result.get('errors'):
                    logger.warning(f"수집 중 오류 발생: {result['errors'][:3]}...")

            elif task_type == TaskType.EVALUATION:
                strategy = TradingStrategy()
                logger.info("전 종목 평가 시작...")
                count = strategy.evaluate_all()
                result_msg = f"평가 완료: {count}개 종목 업데이트됨"

            elif task_type == TaskType.AUTO_TRADE:
                logger.info("자동매매 로직 실행 시작...")
                trader = AutoTrader()
                log_output = trader.run()
                
                # 로그 메시지가 너무 길면 요약
                summary = log_output.replace('\n', ', ')
                if len(summary) > 100:
                    summary = summary[:100] + "..."
                
                result_msg = f"{summary}"
                logger.info(f"자동매매 상세 결과:\n{log_output}")

            else:
                result_msg = f"알 수 없는 작업 유형: {task_type}"
                logger.warning(result_msg)

            self._log_end(log_id, "success", result_msg)
            logger.info(f"===== [{schedule_name}] 작업 완료: {result_msg} =====")

        except Exception as e:
            logger.error(f"===== [{schedule_name}] 작업 실패: {e} =====", exc_info=True)
            self._log_end(log_id, "failed", error_msg=str(e))

    def _log_start(self, task_type, name):
        try:
            with get_session() as session:
                log = ScheduleLog(
                    # schedule_id는 논리적 그룹 ID 역할 (PK는 자동생성)
                    schedule_id=f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    schedule_name=name,
                    task_type=task_type,
                    status="running",
                    start_time=datetime.now()
                )
                session.add(log)
                session.commit()
                return log.id # 자동 생성된 PK 반환
        except Exception as e:
            logger.error(f"로그 시작 기록 실패: {e}")
            return 0

    def _log_end(self, log_id, status, msg=None, error_msg=None):
        if not log_id: return
        try:
            with get_session() as session:
                log = session.query(ScheduleLog).filter(ScheduleLog.id == log_id).first()
                if log:
                    log.status = status
                    log.end_time = datetime.now()
                    log.message = msg
                    log.error_message = error_msg
                    session.commit()
        except Exception as e:
            logger.error(f"로그 종료 기록 실패: {e}")

def get_scheduler() -> SchedulerService:
    return SchedulerService()