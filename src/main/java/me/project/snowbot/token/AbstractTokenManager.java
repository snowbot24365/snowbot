package me.project.snowbot.token;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;

import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Value;

/**
 * `TokenManager` 인터페이스의 공통적인 기능을 구현한 추상 클래스이다.
 * <p>
 * 실제 외부 API 서버와 통신하여 토큰을 발급(generate)받고,
 * 응답받은 JSON 데이터에서 토큰을 파싱(parse)하는 핵심 로직을 담당한다.
 * 토큰의 조회(get) 및 저장(save) 방식은 구현체에 따라 다르므로 하위 클래스에 위임한다.
 * </p>
 */
public abstract class AbstractTokenManager implements TokenManager {

    /** Spring 환경 설정 파일로부터 주입받는 API 앱 키(AppKey)이다. */
    @Value("${kis.auth.appkey}")
    private String appKey;

    /** Spring 환경 설정 파일로부터 주입받는 API 앱 시크릿(AppSecret)이다. */
    @Value("${kis.auth.appsecret}")
    private String appSecret;

    /**
     * 한국투자증권 API 서버로 HTTP POST 요청을 보내 새로운 접근 토큰을 발급받는 메서드이다.
     * <p>
     * 발급 성공 시 토큰을 파싱하고, 만료 시간을 설정하여 저장 메서드를 호출한 뒤 토큰 값을 반환한다.
     * 통신 과정에서 오류 발생 시 RuntimeException을 발생시킨다.
     * </p>
     *
     * @return 발급받은 새로운 Access Token 문자열이다.
     */
    @Override
    public String generateAccessToken() {
        // 1. 요청 URL 및 본문(Body) 데이터 생성
        String url = String.format("%s/oauth2/tokenP",  ApiConfig.REST_BASE_URL);
        String body = String.format(
                "{\"grant_type\":\"client_credentials\",\"appkey\":\"%s\",\"appsecret\":\"%s\"}",
                appKey,
                appSecret
        );

        try {
            // 2. HTTP 연결 설정 (POST 방식, 헤더 설정)
            URL obj = new URL(url);
            HttpURLConnection con = (HttpURLConnection) obj.openConnection();
            con.setRequestMethod("POST");
            con.setRequestProperty("Content-Type", "application/json");

            // 3. 요청 데이터 전송 (Output Stream 활용)
            con.setDoOutput(true);
            try (DataOutputStream wr = new DataOutputStream(con.getOutputStream())) {
                wr.write(body.getBytes(StandardCharsets.UTF_8));
            }

            // 4. 응답 코드 확인 및 예외 처리
            int responseCode = con.getResponseCode();
            if (responseCode != HttpURLConnection.HTTP_OK) {
                throw new RuntimeException("액세스 토큰을 가져올 수 없습니다. 응답 코드: " + responseCode);
            }

            // 5. 응답 데이터 읽기 (Input Stream 활용)
            StringBuilder response;
            try (BufferedReader in = new BufferedReader(new InputStreamReader(con.getInputStream()))) {
                String inputLine;
                response = new StringBuilder();
                while ((inputLine = in.readLine()) != null) {
                    response.append(inputLine);
                }
            }

            // 6. 토큰 파싱 및 저장 후 반환
            // 응답 JSON 문자열을 가져온다.
            String responseJson = response.toString();
            // JSON에서 access_token 값만 추출한다.
            String accessToken = parseAccessToken(responseJson);
            // 토큰 만료 시간을 현재 시간으로부터 23시간 후로 설정한다 (정책상 하루이므로 여유를 둠).
            LocalDateTime expiryDate = LocalDateTime.now().plusHours(23);
            // 추출한 토큰과 만료 시간을 저장소에 저장한다 (구현체가 처리).
            saveToken(accessToken, expiryDate);

            return accessToken;
        } catch (Exception e) {
            // 통신 중 발생한 모든 예외를 런타임 예외로 감싸서 던진다.
            throw new RuntimeException("액세스 토큰을 가져올 수 없습니다.", e);
        }
    }

    /**
     * API 요청 결과로 받은 JSON 문자열에서 실제 접근 토큰 값만 추출하는 메서드이다.
     *
     * @param responseJson 서버로부터 받은 원본 JSON 문자열이다.
     * @return 추출된 "access_token" 값이다.
     */
    @Override
    public String parseAccessToken(String responseJson) {
        JSONObject jsonObject = new JSONObject(responseJson);
        return jsonObject.getString("access_token");
    }
}