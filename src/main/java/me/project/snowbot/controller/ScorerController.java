package me.project.snowbot.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.service.ScorerService;
import me.project.snowbot.service.SlackService;

/**
 * 스윙 종목 발굴을 위한 스코어링 작업을 트리거(Trigger)하는 컨트롤러 클래스이다.
 * 정해진 스케줄에 따라 자동으로 실행되거나, API 호출을 통해 수동으로 실행할 수 있다.
 */
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/scorer")
public class ScorerController {

    private final ScorerService scorerService;
    private final SlackService slackService;

    /**
     * 매일 새벽 5시(KST)에 자동으로 실행되어 스윙 종목 분석 작업을 수행하는 메서드이다.
     * 작업의 시작과 종료, 그리고 예외 발생 상황을 슬랙(Slack) 메시지로 알린다.
     *
     * @return 작업 실행 결과를 담은 ResponseEntity 객체이다.
     */
    @Scheduled(cron = "0 0 5 * * *", zone = "Asia/Seoul") // Executes at 5:00 AM every day
    @GetMapping("/swingitems")
    public ResponseEntity<String> executeSwingItems() {
        // 1. 작업 시작 로그를 기록하고 슬랙 알림을 전송한다.
        log.info("Execute executeSwingItems Start");
        slackService.sendMessage("스윙 종목 분석 작업을 시작한다.");

        try {
            // 2. 스코어링 서비스의 핵심 로직을 실행하여 전 종목을 분석 및 저장한다.
            scorerService.executeSwingScoring();
            
            // 3. 작업이 정상적으로 완료되면 알림을 전송하고 성공 응답을 반환한다.
            slackService.sendMessage("스윙 종목 분석 작업을 완료했다.");
            log.info("Execute executeSwingItems End");
            return ResponseEntity.ok("Execute executeSwingItems End");
        } catch (Exception e) {
            // 4. 예외 발생 시 에러 로그를 남기고, 슬랙으로 에러 메시지를 전송한다.
            log.error("Error during swing items execution", e);
            slackService.sendMessage("스윙 종목 분석 작업 중 오류 발생: " + e.getMessage());
            return ResponseEntity.internalServerError().body("Error: " + e.getMessage());
        }
    }
}