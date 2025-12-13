package me.project.snowbot.token;

import org.springframework.stereotype.Service;

import lombok.AllArgsConstructor;

/**
 * 비즈니스 로직에서 접근 토큰(Access Token)이 필요할 때 사용하는 서비스 클래스이다.
 * <p>
 * 실제 토큰의 발급, 저장, 만료 관리 등 복잡한 로직은 `TokenManager` 인터페이스의 구현체에게 위임하고,
 * 이 클래스는 외부(다른 서비스나 컨트롤러 등)에 단순화된 토큰 조회 메서드를 제공하는 파사드(Facade) 역할을 한다.
 * </p>
 * <p>
 * `@Service` 어노테이션에 의해 스프링 빈으로 등록되며,
 * Lombok의 `@AllArgsConstructor`를 통해 생성자 주입 방식으로 `TokenManager` 의존성을 주입받는다.
 * </p>
 */
@AllArgsConstructor
@Service
public class TokenManagerService {

    /**
     * 실제 토큰 관리 로직을 수행하는 `TokenManager` 인터페이스의 구현체이다.
     * 생성자를 통해 주입받으며, `final`로 선언되어 객체 생성 후 변경되지 않음(불변성)을 보장한다.
     */
    private final TokenManager tokenManager;

    /**
     * 유효한 접근 토큰을 조회하여 반환하는 메서드이다.
     * <p>
     * 내부적으로 주입받은 `tokenManager`에게 실제 토큰 조회 작업을 위임한다.
     * 호출자는 토큰이 파일에 있는지, DB에 있는지, 새로 발급받았는지 알 필요 없이
     * 이 메서드를 통해 당장 사용 가능한 유효한 토큰을 얻을 수 있다.
     * </p>
     *
     * @param key 토큰을 식별하기 위한 키 값(예: 사용자 ID 등)이다.
     * (구현체에 따라 이 값이 사용되지 않을 수도 있다.)
     * @return API 호출 등에 사용할 수 있는 유효한 Access Token 문자열이다.
     */
    public String getAccessToken(String key) {
        return tokenManager.getAccessToken(key);
    }
}