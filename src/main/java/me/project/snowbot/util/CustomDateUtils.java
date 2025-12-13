package me.project.snowbot.util;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

public class CustomDateUtils {

    /**
     * 어제 날짜를 구하여 "yyyyMMdd" 형식의 문자열로 반환하는 메서드이다.
     * (예: 20231129)
     *
     * @return "yyyyMMdd" 형식으로 변환된 어제 날짜 문자열이다.
     */
    public static String getStringYesterday() {
        // 1. 현재 날짜를 기준으로 하루를 빼서 어제 날짜 정보를 생성한다.
        LocalDate localDate = LocalDate.now().minusDays(1);

        // 2. 날짜 포맷을 "년월일(yyyyMMdd)" 형식으로 지정한다.
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");

        // 3. 어제 날짜를 지정된 포맷의 문자열로 변환하여 반환한다.
        return localDate.format(formatter);
    }

    /**
     * 오늘 날짜를 구하여 "yyyyMMdd" 형식의 문자열로 반환하는 메서드이다.
     * (예: 20231130)
     *
     * @return "yyyyMMdd" 형식으로 변환된 오늘 날짜 문자열이다.
     */
    public static String getStringToday() {
        // 1. 현재 시스템의 로컬 날짜 정보를 가져온다.
        LocalDate localDate = LocalDate.now();

        // 2. 날짜 포맷을 "년월일(yyyyMMdd)" 형식으로 지정한다.
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");

        // 3. 현재 날짜를 지정된 포맷의 문자열로 변환하여 반환한다.
        return localDate.format(formatter);
    }

    /**
     * 오늘 날짜를 기준으로 특정 일수(daysToSubtract)를 뺀 날짜를 구하여
     * "yyyyMMdd" 형식의 문자열로 반환하는 메서드이다.
     *
     * @param daysToSubtract 오늘에서 뺄 일수이다. (예: 1이면 어제, 30이면 30일 전)
     * @return "yyyyMMdd" 형식으로 변환된 계산된 날짜 문자열이다.
     */
    public static String getStringDay(int daysToSubtract) {
        // 1. 현재 시스템의 오늘 날짜 정보를 가져온다.
        LocalDate today = LocalDate.now();

        // 2. 오늘 날짜에서 파라미터로 전달된 일수만큼 뺀 날짜를 계산한다.
        LocalDate subtractedDate = today.minusDays(daysToSubtract);

        // 3. 반환할 날짜의 포맷을 "년월일(yyyyMMdd)" 형식으로 지정한다.
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");

        // 4. 계산된 날짜를 지정된 포맷의 문자열로 변환하여 반환한다.
        return subtractedDate.format(formatter);
    }

    /**
     * 현재 한국 표준시(KST) 기준의 시간을 구하여 "HHmmss" 형식의 문자열로 반환하는 메서드이다.
     * (예: 153045)
     *
     * @return "HHmmss" 형식으로 변환된 현재 시간 문자열이다.
     */
    public static String getTime() {
        // 1. 한국 표준시(Asia/Seoul)의 타임존 정보를 생성한다.
        ZoneId kstZoneId = ZoneId.of("Asia/Seoul");

        // 2. 지정된 타임존(KST)을 기준으로 현재 날짜와 시간 정보를 가져온다.
        LocalDateTime currentDateTime = LocalDateTime.now(kstZoneId);

        // 3. 시간 포맷을 시분초(HHmmss) 형식으로 지정한다.
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("HHmmss");
        
        // 4. 현재 시간을 지정된 포맷의 문자열로 변환하여 반환한다.
        String formattedTime = currentDateTime.format(formatter);

        return formattedTime;
    }
}
