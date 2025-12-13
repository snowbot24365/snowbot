package me.project.snowbot.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.slack.api.Slack;
import com.slack.api.webhook.WebhookResponse;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.Map;

@Slf4j
@Service
public class SlackService {

    // 1. Slack 인스턴스를 한 번만 초기화하여 재사용
    private final Slack slack = Slack.getInstance(); 
    private final ObjectMapper objectMapper = new ObjectMapper(); // JSON 처리를 위한 인스턴스

    // 2. application.yml에서 Webhook URL 주입
    @Value("${webhook.slack.url}")
    private String SLACK_WEBHOOK_URL;

    /**
     * 슬랙 메시지 전송
     **/
    public void sendMessage(String msg) {
        try {
            // 3. Map과 ObjectMapper를 사용하여 안전하게 JSON Payload 생성
            Map<String, String> payloadMap = Map.of("text", msg);
            String payload = objectMapper.writeValueAsString(payloadMap);

            WebhookResponse response = slack.send(SLACK_WEBHOOK_URL, payload);

            // 4. 전송 결과 로깅 (성공 및 오류 상태 확인)
            if (response.getCode() != 200) {
                log.error("슬랙 메시지 전송 실패 ({}): URL={}, 응답 본문={}", 
                          response.getCode(), SLACK_WEBHOOK_URL, response.getBody());
            } else {
                log.info("슬랙 메시지 전송 성공: {}", msg);
            }
        } catch (JsonProcessingException e) {
            // JSON 변환 자체에서 발생한 오류 처리
            log.error("슬랙 Payload JSON 변환 중 오류 발생: {}", e.getMessage());
        } catch (IOException e) {
            // Slack API 통신 중 발생한 네트워크/IO 오류 처리
            log.error("슬랙 Webhook 통신 중 오류 발생: URL={}, 에러 메시지={}", 
                      SLACK_WEBHOOK_URL, e.getMessage());
        } catch (Exception e) {
            // 그 외 예측치 못한 오류 처리
            log.error("슬랙 메시지 전송 중 예측치 못한 오류 발생", e);
        }
    }
}