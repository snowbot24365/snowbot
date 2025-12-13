package me.project.snowbot.token;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

import org.springframework.util.StringUtils;

import lombok.extern.slf4j.Slf4j;

/**
 * 파일 시스템을 기반으로 토큰을 저장하고 관리하는 `TokenManager` 구현체이다.
 * <p>
 * 발급받은 토큰을 로컬 파일에 저장하여, 애플리케이션이 재시작되더라도
 * 유효기간이 남아있다면 API를 재호출하지 않고 기존 토큰을 재사용할 수 있도록 한다.
 * </p>
 */
@Slf4j
public class FileTokenManager extends AbstractTokenManager {
    // 주의: 현재 코드 로직상 읽기 경로와 저장 경로가 서로 다르게 혼용되어 사용되고 있다.
    // 추후 환경(실전/모의)에 따라 하나의 경로로 통일되도록 수정이 필요할 수 있다.
    private static final String TOKEN_FILE_PATH = "src/main/resources/auth/token.txt";

    /**
     * 유효한 접근 토큰을 획득하는 메인 메서드이다.
     * <p>
     * 1. 파일에서 기존 토큰 정보를 읽어온다.
     * 2. 토큰이 없거나, 만료되었거나, 파일을 읽는 중 오류가 발생하면 새 토큰을 발급받는다.
     * 3. 유효한 토큰이 존재하면 해당 토큰을 반환한다.
     * </p>
     *
     * @param key 이 구현체에서는 사용되지 않는다.
     * @return 유효한 Access Token 문자열이다.
     */
    @Override
    public String getAccessToken(String key) {
        String accessToken = "";
        LocalDateTime expiryDate = null;

        // 1. 파일 시스템에서 토큰 및 만료일 정보 읽기를 시도한다.
        try {
            File tokenFile = new File(TOKEN_FILE_PATH);

            // 1-1. 토큰 파일이 존재하지 않는 경우 (최초 실행 등)
            if (!tokenFile.exists()) {
                // 저장할 경로의 디렉토리 존재 여부를 확인하고 없으면 생성한다.
                File directory = new File(TOKEN_FILE_PATH).getParentFile();
                if (directory != null && !directory.exists()) {
                    directory.mkdirs();
                }

                // 빈 파일을 생성한다.
                tokenFile.createNewFile();

                // 파일이 새로 생성되었으므로 즉시 새로운 토큰을 발급받고 저장한다.
                accessToken = generateAccessToken();
                expiryDate = LocalDateTime.now().plusHours(23);
                saveToken(accessToken, expiryDate);

            } else {
                // 1-2. 토큰 파일이 존재하는 경우 내용을 읽어온다.
                try (BufferedReader br = new BufferedReader(new FileReader(tokenFile))) {
                    String token = br.readLine();            // 첫 번째 줄: 토큰 값
                    String expiryDateString = br.readLine(); // 두 번째 줄: 만료 일시

                    // 읽어온 데이터가 모두 유효한 문자열인지 확인한다.
                    if (StringUtils.hasText(token) && StringUtils.hasText(expiryDateString)) {
                        // 문자열로 된 만료 일시를 LocalDateTime 객체로 파싱한다.
                        expiryDate = LocalDateTime.parse(expiryDateString, DateTimeFormatter.ISO_DATE_TIME);
                        accessToken = token; // 파싱 성공 시 임시 변수에 할당한다.
                    } else {
                        log.warn("토큰 파일 내용이 비어있거나 불완전하다.");
                    }
                } catch (IOException e) {
                    log.error("토큰 파일을 읽는 중 오류가 발생하였다.", e);
                } catch (DateTimeParseException e) {
                    log.error("토큰 파일의 날짜 형식이 올바르지 않다.", e);
                }
            }
        } catch (Exception e) {
            // 파일 생성, 읽기, 파싱 등 전 과정에서 예기치 않은 오류 발생 시 안전하게 새 토큰을 발급한다.
            log.error("토큰 파일 처리 중 예외 발생. 새 토큰을 발급한다.", e);
            accessToken = generateAccessToken();
            expiryDate = LocalDateTime.now().plusHours(23);
            saveToken(accessToken, expiryDate);
            log.info("Generated NEW ACCESS_TOKEN via exception recovery: " + accessToken);
            return accessToken; // 새로 발급받은 토큰을 즉시 반환한다.
        }

        // 2. 최종적으로 확보된 토큰의 유효성을 검사한다.
        // 만료일 정보가 존재하고, 현재 시간이 만료일 이전인 경우에만 기존 토큰을 사용한다.
        if (expiryDate != null && LocalDateTime.now().isBefore(expiryDate)) {
            log.info("Using existing valid token: " + accessToken);
        } else {
            // 파일이 없었거나, 내용이 비었거나, 파싱에 실패했거나, 만료된 경우 이곳으로 넘어온다.
            log.info("토큰이 유효하지 않아(만료됨 또는 없음) 새로 발급한다.");
            accessToken = generateAccessToken();
            expiryDate = LocalDateTime.now().plusHours(23);
            saveToken(accessToken, expiryDate);
            log.info("Generated NEW ACCESS_TOKEN: " + accessToken);
        }

        return accessToken;
    }

    /**
     * 발급받은 토큰과 만료 시간을 지정된 파일 경로에 저장하는 메서드이다.
     */
    @Override
    public void saveToken(String token, LocalDateTime expiryDate) {
        // try-with-resources 구문을 사용하여 Writer를 자동으로 닫아준다.
        try (BufferedWriter bw = new BufferedWriter(new FileWriter(TOKEN_FILE_PATH))) {
            // 첫 줄에 토큰 값을 기록한다.
            bw.write(token);
            bw.newLine(); // 줄바꿈
            // 두 번째 줄에 ISO-8601 형식으로 포맷팅된 만료 일시를 기록한다.
            bw.write(expiryDate.format(DateTimeFormatter.ISO_DATE_TIME));
        } catch (Exception e) {
            log.error("토큰을 파일에 저장하는 중 오류가 발생했다.", e);
        }
    }
}