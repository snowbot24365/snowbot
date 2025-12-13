package me.project.snowbot.util;

import java.math.BigDecimal;

/**
 * 데이터 타입 변환을 위한 유틸리티 클래스이다.
 * <p>
 * 다양한 형태의 입력값(Object)을 시스템에서 필요한 특정 데이터 타입(예: BigDecimal)으로
 * 안전하게 변환하는 정적(static) 메서드들을 제공한다.
 * 변환 과정에서 발생할 수 있는 예외를 내부적으로 처리하여 null이나 잘못된 형식의 데이터가 입력되더라도
 * 시스템 오류 없이 기본값(예: 0)을 반환하도록 설계되었다.
 * </p>
 */
public class CustomTypeConvert {

    /**
     * 입력받은 객체(Object)를 `BigDecimal` 타입으로 변환하는 메서드이다.
     * <p>
     * 1. 입력 객체를 문자열로 변환한다.
     * 2. 문자열에서 숫자(0-9), 소수점(.), 마이너스 부호(-)를 제외한 모든 문자를 제거한다 (예: 통화 기호, 콤마 등 제거).
     * 3. 정제된 문자열이 유효한 숫자 형식인지 검증한다.
     * 4. 유효하다면 `BigDecimal`로 변환하여 반환하고, 유효하지 않거나 변환 중 오류가 발생하면 `BigDecimal.ZERO`를 반환한다.
     * </p>
     *
     * @param obj 변환할 대상 객체이다. null을 포함하여 어떤 타입이든 입력될 수 있다.
     * @return 변환된 `BigDecimal` 결과값이다. 입력이 null이거나, 숫자가 아니거나, 변환이 불가능한 경우 `BigDecimal.ZERO`가 반환된다.
     */
    public static BigDecimal convBigDecimal(Object obj) {
        // 입력 객체를 문자열로 변환하고, 숫자 관련 문자(0-9, ., -)를 제외한 모든 문자를 제거한다.
        // 예: "$1,234.56" -> "1234.56", "Abc-12.3d" -> "-12.3", null -> "null" -> "" (모두 제거됨)
        String str = String.valueOf(obj).replaceAll("[^0-9.-]", "");

        // 정제된 문자열이 유효한 숫자 형식(정규식 체크)인지 확인한다.
        // 이 단계에서 빈 문자열, ".", "-." 등 잘못 정제된 결과가 걸러진다.
        if (!isValidNumber(str)) {
            return BigDecimal.ZERO;
        }

        try {
            // 검증을 통과한 문자열을 BigDecimal로 최종 변환한다.
            return new BigDecimal(str);
        } catch (NumberFormatException e) {
            // 만약 isValidNumber를 통과했더라도 BigDecimal 생성자에서 예외가 발생하면 0을 반환한다.
            // (isValidNumber의 정규식이 정확하다면 이곳에 도달할 확률은 낮다.)
            return BigDecimal.ZERO;
        }
    }

    /**
     * 문자열이 유효한 숫자 형식(정수 또는 소수)인지 검증하는 내부 헬퍼 메서드이다.
     *
     * @param str 검증할 문자열이다.
     * @return 문자열이 정규표현식 `-?\d+(\.\d+)?` (선택적 음수 부호 + 하나 이상의 숫자 + 선택적 소수점 이하)과 일치하면 `true`, 그렇지 않으면 `false`이다.
     */
    private static boolean isValidNumber(String str) {
        // -?       : 마이너스 부호가 없거나 하나 있음
        // \d+      : 숫자가 하나 이상 연속됨 (정수부)
        // (\.\d+)? : 소수점(.)과 그 뒤에 따르는 하나 이상의 숫자로 구성된 그룹이 없거나 하나 있음 (소수부)
        return str.matches("-?\\d+(\\.\\d+)?");
    }

    /**
     * 객체(Object)를 Integer 타입으로 변환하는 메서드이다.
     * 입력된 값에서 숫자, 소수점, 부호를 제외한 문자는 제거하며, 변환 실패 시 0을 반환한다.
     *
     * @param obj 변환할 대상 객체이다.
     * @return 변환된 Integer 값이다. 변환 불가 시 0을 반환한다.
     */
    public static Integer convInteger(Object obj) {
        // 1. 객체를 문자열로 변환 후, 숫자(0-9), 소수점(.), 마이너스(-)를 제외한 모든 문자를 공백으로 치환하여 제거한다.
        String str = String.valueOf(obj).replaceAll("[^0-9.-]", "");

        // 2. 정제된 문자열이 유효한 숫자 형식이 아니면 0을 반환한다.
        if (!isValidNumber(str)) return 0;

        try {
            // 3. 정제된 문자열을 정수(Integer)로 파싱하여 반환한다.
            return Integer.parseInt(str);
        } catch (NumberFormatException e) {
            // 4. 파싱 중 오류(예: 소수점이 포함되어 있거나 정수 범위를 초과함)가 발생하면 예외를 처리하고 0을 반환한다.
            return 0;
        }
    }

    /**
     * 객체(Object)를 Double 타입으로 변환하는 메서드이다.
     * 입력된 값에서 숫자, 소수점, 부호를 제외한 문자는 제거하며, 변환 실패 시 0.0을 반환한다.
     *
     * @param obj 변환할 대상 객체이다.
     * @return 변환된 Double 값이다. 변환 불가 시 0.0을 반환한다.
     */
    public static double convDouble(Object obj) {
        // 1. 객체를 문자열로 변환 후, 숫자(0-9), 소수점(.), 마이너스(-)를 제외한 모든 문자를 공백으로 치환하여 제거한다.
        String str = String.valueOf(obj).replaceAll("[^0-9.-]", "");

        // 2. 정제된 문자열이 유효한 숫자 형식이 아니면 0.0을 반환한다.
        if (!isValidNumber(str)) return 0.0;

        try {
            // 3. 정제된 문자열을 실수(Double)로 파싱하여 반환한다.
            return Double.parseDouble(str);
        } catch (NumberFormatException e) {
            // 4. 파싱 중 오류가 발생하면 예외를 처리하고 0.0을 반환한다.
            return 0.0;
        }
    }
}