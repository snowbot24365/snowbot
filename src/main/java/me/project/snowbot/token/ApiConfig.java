package me.project.snowbot.token;

import org.springframework.context.annotation.Configuration;

@Configuration
// API 기본 URL 정보를 담고 있는 설정 클래스이다.
public class ApiConfig {
    // 실제 투자 API 기본 URL
    public static final String REST_BASE_URL = "https://openapi.koreainvestment.com:9443";
    // 모의 투자 API 기본 URL
    public static final String MOK_BASE_URL = "https://openapivts.koreainvestment.com:29443";

    public static final String FHKST01010100_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price";     //주식현재가 시세

    public static final String FHKST66430100_PATH = "/uapi/domestic-stock/v1/finance/balance-sheet";   //국내주식 대차대조표
    public static final String FHKST66430200_PATH = "/uapi/domestic-stock/v1/finance/income-statement"; //국내주식 손익계산서
    public static final String FHKST66430300_PATH = "/uapi/domestic-stock/v1/finance/financial-ratio";  //국내주식 재무비율
    public static final String FHKST66430400_PATH = "/uapi/domestic-stock/v1/finance/profit-ratio";     //국내주식 수익성비율
    public static final String FHKST66430500_PATH = "/uapi/domestic-stock/v1/finance/other-major-ratios";   //국내주식 기타주요비율

    public static final String FHKST03010100_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice";  //국내주식기간별시세(일/주/월/년)

    public static final String ACCOUNT_BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance";    // 계좌 잔고 조회 API 경로
    public static final String FHKST01010400_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-price";   //주식현재가 일자별 시세

    public static final String ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash";    // 주문 접수 API 경로
}
