package me.project.snowbot.token;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 토큰 관리(Token Management)와 관련된 스프링 빈(Bean)을 정의하고 설정하는 클래스이다.
 * <p>
 * `@Configuration` 어노테이션이 부착되어 있어, 스프링 부트가 초기화될 때
 * 이 클래스를 환경 설정 클래스로 인식하고 내부의 `@Bean` 메서드들을 실행하여 컨테이너에 등록한다.
 * </p>
 */
@Configuration
public class TokenConfig {

    /**
     * `TokenManager` 인터페이스에 대한 실제 구현체를 스프링 빈으로 생성하고 등록하는 메서드이다.
     * <p>
     * 이 메서드는 `TokenManager` 타입의 빈을 요청하는 곳에 `FileTokenManager` 인스턴스를 제공하도록 설정한다.
     * 즉, 현재 애플리케이션은 파일 시스템을 기반으로 토큰을 관리하는 구현체를 사용하게 된다.
     * </p>
     * <p>
     * 만약 나중에 DB 기반이나 Redis 기반 등으로 구현체를 변경하고 싶다면,
     * 이 메서드의 반환값만 다른 구현체로 변경하면 되므로 유지보수성이 높아진다.
     * </p>
     *
     * @return 스프링 컨텍스트에서 관리될 `TokenManager`의 구현체 (현재는 `FileTokenManager`)
     */
    @Bean
    public TokenManager tokenManager() {
        // FileTokenManager가 @Component를 가지고 있지 않더라도,
        // 이 설정 클래스를 통해 명시적으로 빈으로 등록된다.
        return new FileTokenManager();
    }
}