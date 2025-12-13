package me.project.snowbot.token;

import java.time.LocalDateTime;

/**
 * 한국투자증권 API 접근 토큰(Access Token)을 관리하는 인터페이스이다.
 * <p>
 * 토큰의 발급, 파싱, 저장 및 조회를 담당하며,
 * 불필요한 API 호출을 최소화하기 위해 토큰 캐싱 및 관리 역할을 수행한다.
 * </p>
 */
public interface TokenManager {

    /**
     * 유효한 접근 토큰을 조회하는 기능이다.
     * <p>
     * 저장된 토큰이 있고 유효 기간이 남아있다면 해당 토큰을 반환하며,
     * 만료되었거나 존재하지 않으면 내부 로직에 따라 토큰 재발급 과정을 수행한 후 반환한다.
     * </p>
     *
     * @param key 토큰을 식별하기 위한 키 값(예: 사용자 ID 또는 AppKey 등)이다.
     * @return 사용 가능한 Access Token 문자열이다.
     */
    String getAccessToken(String key);

    /**
     * 한국투자증권 API 서버에 요청하여 새로운 접근 토큰을 발급받는 기능이다.
     * <p>
     * 실제로 외부 API 통신(HTTP 요청)이 발생하는 메서드이다.
     * </p>
     *
     * @return API로부터 응답받은 원본 결과 데이터(주로 JSON 문자열)이다.
     */
    String generateAccessToken();

    /**
     * API 응답(JSON) 데이터를 파싱하여 필요한 토큰 정보만 추출하는 기능이다.
     *
     * @param responseJson API 요청 결과로 전달받은 원본 JSON 문자열이다.
     * @return 파싱하여 추출된 Access Token 문자열이다.
     */
    String parseAccessToken(String responseJson);

    /**
     * 발급받은 토큰 정보와 만료 시간을 저장소에 저장하는 기능이다.
     * <p>
     * 구현체에 따라 메모리, 데이터베이스 등 저장 방식이 결정된다.
     * </p>
     *
     * @param token      저장할 Access Token 값이다.
     * @param expiryDate 해당 토큰의 만료 일시이다.
     */
    void saveToken(String token, LocalDateTime expiryDate);
}