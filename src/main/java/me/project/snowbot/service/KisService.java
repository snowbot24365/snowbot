package me.project.snowbot.service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.function.IntFunction;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.Body;
import me.project.snowbot.dto.IndexData;
import me.project.snowbot.dto.SheetData;
import me.project.snowbot.dto.TwoArrData;
import me.project.snowbot.token.ApiConfig;
import me.project.snowbot.token.TokenManagerService;
import me.project.snowbot.util.CustomDateUtils;

/**
 * KIS API를 사용하여 주식 관련 정보를 조회하는 서비스 클래스입니다.
 * <p>
 * API 호출 시 토큰 관리, 재시도 로직, 호출 간격 제어 기능을 제공합니다.
 * 현재는 HttpURLConnection을 사용하여 통신합니다.
 * </p>
 */
@Slf4j
@Service
public class KisService {

    @Autowired
    private TokenManagerService tokenManagerService;

    private final WebClient webClient;

    /** API 호출 실패 시 최대 재시도 횟수 */
    int maxRetries = 3;

    /** 재시도 간의 대기 시간(밀리초) */
    int retryIntervalMillis = 1000;

    /** API 호출 간의 최소 대기 시간(밀리초) */
    int callIntervalMillis = 1000;

    @Value("${kis.auth.appkey}")
    private String appKey;

    @Value("${kis.auth.appsecret}")
    private String appSecret;

    /**
     * WebClient를 초기화하는 생성자입니다.
     *
     * @param webClientBuilder WebClient 빌더
     */
    public KisService(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.baseUrl(ApiConfig.REST_BASE_URL).build();
    }

    /**
     * HTTP GET 요청을 보내고 응답을 지정된 타입으로 변환하여 반환합니다.
     */
    private <T> T sendGetRequest(String path, String query, String tr_id, String accessToken, String appKey, String appSecret, Class<T> responseType) throws IOException {
        URL url = new URL(path + query);
        HttpURLConnection con = (HttpURLConnection) url.openConnection();
        con.setRequestMethod("GET");
        con.setRequestProperty("Content-Type", "application/json");
        con.setRequestProperty("Authorization", "Bearer " + accessToken);
        con.setRequestProperty("appkey", appKey);
        con.setRequestProperty("appsecret", appSecret);
        con.setRequestProperty("tr_id", tr_id);

        StringBuilder response = new StringBuilder();
        try (BufferedReader in = new BufferedReader(new InputStreamReader(con.getInputStream(), StandardCharsets.UTF_8))) {
            String inputLine;
            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }
        }

        ObjectMapper objectMapper = new ObjectMapper();
        return objectMapper.readValue(response.toString(), responseType);
    }

    /**
     * HTTP POST 요청을 보내고 응답을 지정된 타입으로 변환하여 반환합니다.
     */
    private <T> T sendPostRequest(String path, String query, String tr_id, String accessToken, String appKey, String appSecret, Class<T> responseType) throws IOException {
        URL url = new URL(path);
        HttpURLConnection con = (HttpURLConnection) url.openConnection();
        con.setRequestMethod("POST");
        con.setRequestProperty("Content-Type", "application/json");
        con.setRequestProperty("Authorization", "Bearer " + accessToken);
        con.setRequestProperty("appkey", appKey);
        con.setRequestProperty("appsecret", appSecret);
        con.setRequestProperty("tr_id", tr_id);

        con.setDoOutput(true);
        OutputStreamWriter writer = new OutputStreamWriter(con.getOutputStream(), StandardCharsets.UTF_8);
        writer.write(query);
        writer.flush();

        StringBuilder response = new StringBuilder();
        try (BufferedReader in = new BufferedReader(new InputStreamReader(con.getInputStream(), StandardCharsets.UTF_8))) {
            String inputLine;
            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }
        }

        ObjectMapper objectMapper = new ObjectMapper();
        return objectMapper.readValue(response.toString(), responseType);
    }

    // ... 나머지 메서드 (executeWithRetry, callInterval, getEquities)는 기존과 동일합니다 ...
    /**
     * 재시도 로직을 포함하여 API 요청을 수행하는 제네릭 메서드입니다.
     *
     * @param path API 엔드포인트 경로
     * @param query 쿼리 문자열 또는 요청 본문
     * @param tr_id 트랜잭션 ID
     * @param responseType 응답 타입 클래스
     * @param methodType HTTP 메서드 타입 ("GET" 또는 "POST")
     * @param <T> 응답 타입
     * @return 변환된 응답 객체 (실패 시 null 반환)
     */
    private <T> T executeWithRetry(
            String path,
            String query,
            String tr_id,
            Class<T> responseType,
            String methodType
    ) {
        String accessToken = tokenManagerService.getAccessToken(appKey);

        int retryCount = 0;
        T response = null;

        callInterval(); // 호출 간격 제어

        while (retryCount < maxRetries) {
            try {
                // GET 또는 POST 요청 구분
                if ("GET".equalsIgnoreCase(methodType)) {
                    response = sendGetRequest(path, query, tr_id, accessToken, appKey, appSecret, responseType);
                } else if ("POST".equalsIgnoreCase(methodType)) {
                    response = sendPostRequest(path, query, tr_id, accessToken, appKey, appSecret, responseType);
                }
                break; // 성공 시 루프 종료
            } catch (IOException e) {
                log.error("재시도 중 오류 발생: " + e.getMessage());
            }

            try {
                Thread.sleep(retryIntervalMillis); // 재시도 전 대기
            } catch (InterruptedException e) {
                log.error(e.getMessage());
                Thread.currentThread().interrupt(); // 인터럽트 상태 복원
            }

            retryCount++;
        }

        if (retryCount == maxRetries) {
            log.info("최대 재시도 횟수를 초과하여 요청을 처리할 수 없습니다.");
        }

        return response;
    }

    /**
     * API 호출 간의 최소 대기 시간을 준수하기 위한 메서드입니다.
     */
    private void callInterval() {
        try {
            Thread.sleep(callIntervalMillis);
        } catch (InterruptedException e) {
            log.error(e.getMessage());
            Thread.currentThread().interrupt(); // 인터럽트 상태 복원
        }
    }

    /**
     * 주식 현재가 시세를 조회합니다. [v1_국내주식-008]
     *
     * @param id 종목 코드 (예: "A005930")
     * @return 주식 현재가 정보가 담긴 Body 객체
     */
    public Body getEquities(String id) {
        String path = ApiConfig.REST_BASE_URL + ApiConfig.FHKST01010100_PATH;
        String tr_id = "FHKST01010100";
        String query = "?fid_cond_mrkt_div_code=J&fid_input_iscd=" + id.replace("A", "");

        return executeWithRetry(path, query, tr_id, Body.class, "GET");
    }

    /**
     * 재무제표 유형(flag)별 API 경로와 트랜잭션 ID(TR ID)를 매핑한 상수 맵이다.
     * <ul>
     * <li><b>B</b>: 대차대조표 (Balance Sheet)</li>
     * <li><b>I</b>: 손익계산서 (Income Statement)</li>
     * <li><b>F</b>: 현금흐름표 (Cash Flow Statement)</li>
     * <li><b>P</b>: 손익 및 현금흐름표 (Profit & Loss and Cash Flow)</li>
     * <li><b>E</b>: 기업 가치 지표 (Enterprise Value)</li>
     * </ul>
     * 각 키(flag)는 [0: 전체 API 경로, 1: TR ID] 배열에 매핑된다.
     */
    private static final Map<String, String[]> SHEET_CD_MAP = Map.of(
            "B", new String[]{ApiConfig.REST_BASE_URL + ApiConfig.FHKST66430100_PATH, "FHKST66430100"},
            "I", new String[]{ApiConfig.REST_BASE_URL + ApiConfig.FHKST66430200_PATH, "FHKST66430200"},
            "F", new String[]{ApiConfig.REST_BASE_URL + ApiConfig.FHKST66430300_PATH, "FHKST66430300"},
            "P", new String[]{ApiConfig.REST_BASE_URL + ApiConfig.FHKST66430400_PATH, "FHKST66430400"},
            "E", new String[]{ApiConfig.REST_BASE_URL + ApiConfig.FHKST66430500_PATH, "FHKST66430500"}
    );

    /**
     * 지정된 유형(flag)의 재무제표 데이터를 KIS API를 통해 조회하는 메서드이다.
     * <p>
     * 입력받은 `flag`를 사용하여 `SHEET_CD_MAP`에서 적절한 API 경로와 TR ID를 매핑한다.
     * 그 후, 재시도 로직이 포함된 `executeWithRetry` 메서드를 호출하여 실제 API 요청을 수행한다.
     * </p>
     *
     * @param flag 재무제표 유형을 나타내는 단일 문자 코드이다. (B, I, F, P, E 중 하나)
     * @param id 조회할 종목 코드이다. (예: "A005930")
     * @param cls 재무제표의 결산 주기를 나타내는 코드이다. (0: 연간, 1: 분기)
     * @return 조회된 재무제표 데이터가 담긴 `SheetData` 객체이다.
     * @throws IllegalArgumentException 지원하지 않는 `flag` 값이 입력된 경우 예외가 발생한다.
     */
    public SheetData getSheets(String flag, String id, String cls) {
        // 1. Map에서 flag에 해당하는 API 정보(경로 및 TR ID) 배열을 가져온다.
        String[] pathTrId = SHEET_CD_MAP.get(flag);

        // 2. 잘못된 flag 입력에 대한 방어 로직을 수행한다.
        if (pathTrId == null) {
            throw new IllegalArgumentException("Invalid flag value: " + flag);
        }

        // 3. 배열에서 API 경로와 TR ID를 각각 추출한다.
        String path = pathTrId[0];
        String tr_id = pathTrId[1];

        // 4. API 호출을 위한 쿼리 스트링을 구성한다.
        // 종목 코드에서 'A'를 제거하고, 결산 주기(cls)를 포함한다.
        String query = "?fid_cond_mrkt_div_code=J&fid_input_iscd=" + id.replace("A", "") +
                "&FID_DIV_CLS_CODE=" + cls;

        // 5. 재시도 로직이 적용된 공통 메서드를 통해 GET 요청을 실행하고 결과를 반환한다.
        return executeWithRetry(path, query, tr_id, SheetData.class, "GET");
    }

    // 한 번에 조회할 횟수와 데이터 크기를 상수로 정의한다. (총 400일 데이터 조회)
    private final int EPOCH = 4;
    private final int BATCH_SIZE = 100;

    /**
     * 종목의 차트(시세) 데이터를 조회하여 리스트로 반환하는 메서드이다.
     * 오늘 데이터만 필요한 경우 단건 조회하고, 전체 히스토리가 필요한 경우 병렬 또는 반복 조회를 수행한다.
     *
     * @param id 종목 코드이다.
     * @param bToday 오늘 데이터만 조회할지 여부이다. (true: 오늘만, false: 400일치)
     * @return 조회된 인덱스 데이터 리스트이다.
     */
    public List<IndexData> getItemChartPrice(String id, boolean bToday) {
        return bToday
                // 1. 오늘 데이터만 요청할 경우, 시작일과 종료일을 오늘 날짜로 설정하여 단건 리스트를 생성한다.
                ? List.of(fetchItemChartPrice(id, CustomDateUtils.getStringToday(), CustomDateUtils.getStringToday()))
                // 2. 과거 데이터가 필요한 경우, 0부터 3까지(EPOCH) 반복하며 100일(BATCH_SIZE) 단위로 날짜 구간을 나눈다.
                : IntStream.range(0, EPOCH)
                .mapToObj((IntFunction<IndexData>) i -> {
                    // 3. 조회 시작일(과거)과 종료일(최근)의 오프셋을 계산한다.
                    // 예: i=0 -> from=99일전, to=0일전(오늘) / i=1 -> from=199일전, to=100일전
                    int from = ((i + 1) * BATCH_SIZE) - 1;
                    int to = i * BATCH_SIZE;
                    // 4. 계산된 날짜 문자열을 사용하여 API를 호출하고 결과를 반환한다.
                    return fetchItemChartPrice(id, CustomDateUtils.getStringDay(from), CustomDateUtils.getStringDay(to));
                })
                // 5. 조회된 결과들을 리스트로 수집하여 반환한다.
                .collect(Collectors.toList());
    }

    /**
     * 실제 외부 API를 호출하여 특정 기간의 종목 시세를 가져오는 내부 메서드이다.
     * 한국투자증권의 주식 기간별 시세 조회(FHKST03010100) API를 사용한다.
     *
     * @param id 종목 코드이다.
     * @param from 조회 시작 날짜 문자열이다. (YYYYMMDD)
     * @param to 조회 종료 날짜 문자열이다. (YYYYMMDD)
     * @return API 호출 결과가 매핑된 IndexData 객체이다.
     */
    private IndexData fetchItemChartPrice(String id, String from, String to) {
        String path = ApiConfig.REST_BASE_URL + ApiConfig.FHKST03010100_PATH;
        String tr_id = "FHKST03010100"; // 국내주식 기간별 시세(일/주/월/년) 조회 TR ID이다.

        // 1. 쿼리 파라미터를 구성한다.
        // fid_cond_mrkt_div_code=J (주식), fid_period_div_code=D (일봉), fid_org_adj_prc=1 (수정주가 반영)
        // 종목 코드(id) 앞에 붙은 'A' 등의 문자는 제거한다.
        String query = "?fid_cond_mrkt_div_code=J&fid_input_iscd=" + id.replace("A", "") +
                "&fid_input_date_1=" + from + "&fid_input_date_2=" + to + "&fid_period_div_code=D&fid_org_adj_prc=1";

        // 2. 재시도 로직이 포함된 실행 메서드(executeWithRetry)를 호출하여 데이터를 요청한다.
        return executeWithRetry(path, query, tr_id, IndexData.class, "GET");
    }

    /**
     * 한국투자증권 API를 호출하여 계좌의 주식 잔고 및 예수금 현황을 조회하는 메서드이다.
     * output1은 보유 종목별 상세 내역(수량, 수익률 등)을, output2는 계좌 전체의 자산 현황(예수금, 평가금액 등)을 포함한다.
     *
     * @param accountNo 종합 계좌 번호 (8자리)이다.
     * @param accountCd 계좌 상품 코드 (2자리)이다.
     * @param cl 조회 구분 코드이다. (01: 대출일별, 02: 종목별)
     * @return 보유 종목 리스트(output1)와 계좌 자산 정보(output2)를 포함한 데이터 객체이다.
     */
    public TwoArrData getAccountBalance(String accountNo, String accountCd, String cl) {
        // 1. 모의투자계좌 API 호출 경로와 주식 잔고 조회용 TR ID를 설정한다.
        String path = ApiConfig.MOK_BASE_URL + ApiConfig.ACCOUNT_BALANCE_PATH;
        String tr_id = "VTTC8434R"; // 주식 잔고 및 예수금 현황 조회 (모의투자)
        // String path = ApiConfig.REST_BASE_URL + ApiConfig.ACCOUNT_BALANCE_PATH;  // 실전투자용 경로
        // String tr_id = "TTTC8434R"; // 주식 잔고 및 예수금 현황 조회 (실전투자)

        // 2. 요청에 필요한 쿼리 파라미터를 구성한다.
        // CTX_AREA_FK100, NK100은 연속 조회(Paging) 시 사용되나, 여기서는 첫 페이지만 조회하도록 공란으로 설정한다.
        String query = new StringBuilder()
                .append("?CANO=").append(accountNo)              // 계좌번호
                .append("&ACNT_PRDT_CD=").append(accountCd)      // 상품코드 (01 등)
                .append("&AFHR_FLPR_YN=N")                       // 시간외 단일가 여부 (N: 미포함)
                .append("&OFL_YN=")                              // 오프라인 여부 (공란)
                .append("&INQR_DVSN=").append(cl)                // 조회구분 (01: 대출일별, 02: 종목별)
                .append("&UNPR_DVSN=01")                         // 단가구분 (01: 기본값)
                .append("&FUND_STTL_ICLD_YN=N")                  // 펀드결제분 포함여부 (N: 미포함)
                .append("&FNCG_AMT_AUTO_RDPT_YN=N")              // 융자금액 자동상환 여부 (N: 미포함)
                .append("&PRCS_DVSN=01")                         // 처리구분 (00: 전일매매포함, 01: 전일매매미포함)
                .append("&CTX_AREA_FK100=")                      // 연속조회 키 (Forward)
                .append("&CTX_AREA_NK100=")                      // 연속조회 키 (Next)
                .toString();

        // 3. 재시도 로직이 포함된 실행 메서드를 호출하여 API 요청을 보낸다.
        return executeWithRetry(path, query, tr_id, TwoArrData.class, "GET");
    }

    /**
     * 특정 종목의 일자별 시세(현재가) 데이터를 조회하는 메서드이다.
     * 한국투자증권 API의 '주식현재가 일자별(FHKST01010400)' TR을 사용하여 최근 30일간의 데이터를 가져온다.
     *
     * @param id 종목 코드이다. (예: 005930)
     * @return 일자별 시세 데이터가 담긴 SheetData 객체이다.
     */
    public SheetData getDailyPrice(String id) {
        // 1. API 기본 경로와 해당 기능의 TR ID(FHKST01010400)를 설정한다.
        String path = ApiConfig.REST_BASE_URL + ApiConfig.FHKST01010400_PATH;
        String tr_id = "FHKST01010400"; // 국내주식 기간별 시세(일/주/월/년)

        // 2. 요청 파라미터를 구성한다.
        // fid_cond_mrkt_div_code=J (주식)
        // FID_PERIOD_DIV_CODE=D (일봉 기준)
        // FID_ORG_ADJ_PRC=0 (수정주가 미반영 - 0:미반영, 1:반영)
        // 종목 코드(id)에 'A' 접두사가 있다면 제거하여 표준 코드로 변환한다.
        String query = "?fid_cond_mrkt_div_code=J&fid_input_iscd=" + id.replace("A", "") + "&FID_PERIOD_DIV_CODE=D&FID_ORG_ADJ_PRC=0";

        // 3. 재시도 로직이 포함된 메서드를 통해 API를 호출하고 결과를 반환한다.
        return executeWithRetry(path, query, tr_id, SheetData.class, "GET");
    }

    /**
     * 주식의 현금 매수 또는 매도 주문을 실행하는 메서드이다.
     * 모의투자(VTTC)와 실전투자(TTTC) TR ID를 구분하여 처리하며, API 규격에 맞는 JSON 바디를 생성하여 요청한다.
     *
     * @param order_type 주문 유형이다. ("B": 매수, "S": 매도)
     * @param id 종목 코드이다. (상품번호, PDNO)
     * @param cano 종합 계좌 번호이다. (8자리)
     * @param dvsn 주문 구분 코드이다. ("00": 지정가, "01": 시장가 등)
     * @param qty 주문 수량이다.
     * @param unpr 주문 단가이다.
     * @return API 호출 결과가 담긴 Body 객체이다.
     */
    public Body orderItem(String order_type, String id, String cano, String dvsn, int qty, int unpr) {
        // 1. API 호출 경로를 설정한다. (현재는 모의투자 Base URL 사용 중)
        String path = ApiConfig.MOK_BASE_URL + ApiConfig.ORDER_PATH;
        // String path = ApiConfig.REST_BASE_URL + ApiConfig.ORDER_PATH;    // 실전투자용 경로

        // 2. 모의투자용 매수/매도 TR ID 매핑이다.
        Map<String, String> mockMap = Map.of(
                "B", "VTTC0012U", // 주식 현금 매수 주문 (모의)
                "S", "VTTC0011U"  // 주식 현금 매도 주문 (모의)
        );

        // 3. 실전투자용 매수/매도 TR ID 매핑이다.
        Map<String, String> realMap = Map.of(
                "B", "TTTC0012U", // 주식 현금 매수 주문 (실전)
                "S", "TTTC0011U"  // 주식 현금 매도 주문 (실전)
        );

        // 4. 입력된 주문 유형(order_type)이 유효한지 검증한다.
        if (!mockMap.containsKey(order_type) || !realMap.containsKey(order_type)) {
            throw new IllegalArgumentException("Invalid order_type: " + order_type);
        }

        // 5. 사용할 TR ID를 선택한다. (현재는 모의투자용 ID를 사용하도록 설정되어 있다.)
        String tr_id = mockMap.get(order_type); // 모의투자용 TR ID
        //String tr_id = realMap.get(order_type); // 실전투자 전환 시 이 라인의 주석을 해제하여 사용한다.

        // 6. API 요청에 필요한 JSON 형식의 바디 데이터를 생성한다.
        // 계좌번호(CANO), 계좌상품코드(01), 종목번호(PDNO), 주문구분(ORD_DVSN), 수량(ORD_QTY), 단가(ORD_UNPR)를 포함한다.
        String query = String.format("{\n" +
                "    \"CANO\": \"%s\",\n" +
                "    \"ACNT_PRDT_CD\": \"01\",\n" +
                "    \"PDNO\": \"%s\",\n" +
                "    \"ORD_DVSN\": \"%s\",\n" +
                "    \"ORD_QTY\": \"%s\",\n" +
                "    \"ORD_UNPR\": \"%s\"\n" +
                "}", cano, id, dvsn, qty, unpr);

        // 7. 재시도 로직이 포함된 POST 요청을 실행하여 주문을 전송하고 결과를 반환한다.
        return executeWithRetry(path, query, tr_id, Body.class, "POST");
    }
}