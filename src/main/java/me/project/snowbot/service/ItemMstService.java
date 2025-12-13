package me.project.snowbot.service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.ItemMst;
import me.project.snowbot.repository.ItemMstRepository;
import me.project.snowbot.util.CustomDateUtils;

@Slf4j // Lombok 로거(Logger) 자동 생성 (@Slf4j)
@Service // Spring 서비스 계층 컴포넌트 선언
@RequiredArgsConstructor // final 필드에 대한 생성자 자동 생성 (의존성 주입)
public class ItemMstService {

    private final ItemMstRepository itemMstRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // application.yml/properties에서 KRX API URL 값을 주입받는 변수이다.
    @Value("${krx.kospi.url}")
    private String KRX_KOSPI_URL;

    @Value("${krx.kosdaq.url}")
    private String KRX_KOSDAQ_URL;

    // application.yml/properties에서 KRX API 인증 키 값을 주입받는 변수이다.
    @Value("${krx.key}")
    private String KRX_KEY;

    /**
     * 특정 종목 코드(id)에 해당하는 종목 정보를 조회한다.
     *
     * @param id 조회할 종목의 코드(itemCd)이다.
     * @return 조회된 `ItemMst` 엔티티 객체이다. 존재하지 않을 경우 `null`이 반환될 수 있다.
     */
    public ItemMst findByItem(String id) {
        return itemMstRepository.findByOne(id);
    }

    /**
     * 지정된 시장(KOSPI, KOSDAQ)의 종목 정보를 가져오는 메인 메서드이다.
     * API 호출 실패 시 최대 3회까지 재시도를 수행한다.
     */
    public List<Map<String, String>> getItemsInfo(String market) throws Exception {
        int maxRetries = 3;
        int retryCount = 0;

        while (retryCount < maxRetries) {
            try {
                // API로부터 데이터를 가져온 후, HashSet을 사용하여 중복 항목을 제거하고 반환한다.
                return new ArrayList<>(new HashSet<>(fetchData(market)));
            } catch (Exception e) {
                retryCount++;
                log.error("Exception occurred: " + e.getMessage() + ", retrying... (Retry count: " + retryCount + ")");

                if (retryCount == maxRetries) {
                    log.error("Max retries reached. Failing.");
                    throw e; // 모든 재시도가 실패하면 예외를 전파하여 처리를 중단한다.
                }
            }
        }

        // 정상적인 흐름에서는 도달하지 않는 코드이나 컴파일러를 위해 빈 리스트를 반환한다.
        return Collections.emptyList();
    }

    /**
     * 실제 HTTP 요청을 통해 KRX API에서 데이터를 조회하는 메서드이다.
     * 어제 날짜를 기준으로 데이터를 요청한다.
     */
    private List<Map<String, String>> fetchData(String market) throws Exception {
        String path = "";
        // 시장 구분에 따라 요청할 URL을 결정한다.
        if ("KOSPI".equals(market))
            path = KRX_KOSPI_URL;
        else
            path = KRX_KOSDAQ_URL;
            
        // 쿼리 파라미터를 구성한다. 기준일자(basDd)는 어제 날짜로 설정한다.
        String query = new StringBuilder()
                .append("?AUTH_KEY=").append(KRX_KEY)
                .append("&basDd=").append(CustomDateUtils.getStringYesterday())
                .toString().replace("%25", "%");

        // HttpURLConnection 객체를 생성하고 GET 방식을 설정한다.
        URL url = new URL(path + query);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setRequestProperty("Content-type", "application/json");

        // API 호출 결과를 받아온다.
        int responseCode = conn.getResponseCode();
        if (responseCode == HttpURLConnection.HTTP_OK) {
            BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line);
            }
            br.close();

            // JSON 문자열을 파싱 메서드로 전달하여 처리한다.
            String jsonResult = sb.toString();
            return parseJsonResponse(jsonResult);
        } else {
            throw new IOException("Failed to fetch data: HTTP error code " + responseCode);
        }
    }

    /**
     * JSON 형태의 응답 문자열을 파싱하여 필요한 데이터만 추출하는 메서드이다.
     * '보통주'인 항목만 필터링하여 리스트로 반환한다.
     */
    private List<Map<String, String>> parseJsonResponse(String jsonResult) {

        try {
            JsonNode rootNode = objectMapper.readTree(jsonResult);
            // JSON 구조에서 데이터가 위치한 'OutBlock_1' 노드를 추출한다.
            JsonNode itemNode = rootNode.get("OutBlock_1");

            // 노드가 배열 형태가 아니라면 빈 리스트를 반환한다.
            if (!itemNode.isArray()) {
                return Collections.emptyList();
            }

            // Stream API를 사용하여 데이터를 처리한다.
            return StreamSupport.stream(itemNode.spliterator(), false)
                    // 주식 종류가 '보통주'인 것만 필터링한다.
                    .filter(item -> "보통주".equals(item.path("KIND_STKCERT_TP_NM").asText()))
                    // 필요한 필드만 추출하여 Map으로 변환한다.
                    .map(item -> Map.of(
                            "ISU_SRT_CD", item.path("ISU_SRT_CD").asText(),
                            "ISU_ABBRV", item.path("ISU_ABBRV").asText(),
                            "ISU_ENG_NM", item.path("ISU_ENG_NM").asText(),
                            "MKT_TP_NM", item.path("MKT_TP_NM").asText(),
                            "SECT_TP_NM", item.path("SECT_TP_NM").asText()
                    ))
                    .collect(Collectors.toList());

        } catch (Exception e) {
            e.printStackTrace();
            // 파싱 중 오류 발생 시 빈 리스트를 반환한다.
            return Collections.emptyList();
        }
    }

    /**
     * 수집한 종목 정보를 데이터베이스에 저장하는 메서드이다.
     * 이미 존재하는 종목 코드는 제외하고 신규 종목만 Insert한다.
     */
    @Transactional
    public void insert(List<Map<String, String>> items) {
        // DB에 저장된 모든 종목 코드를 미리 조회하여 중복 검사에 사용한다.
        List<String> itemCds = itemMstRepository.findByAllItemCds();

        items.stream()
                .map(item -> {
                    // 종목 코드에서 혹시 모를 'A' 문자를 제거하여 정제한다.
                    String ticker = String.valueOf(item.get("ISU_SRT_CD")).replace("A", "");
                    
                    // 기존 DB에 없는 종목인 경우에만 새로운 엔티티를 생성한다.
                    if (!itemCds.contains(ticker)) {
                        ItemMst newItem = new ItemMst();
                        newItem.setItemCd(ticker);
                        newItem.setMrktCtg(String.valueOf(item.get("MKT_TP_NM")));
                        newItem.setItmsNm(String.valueOf(item.get("ISU_ABBRV")));
                        newItem.setCorpNm(String.valueOf(item.get("ISU_ENG_NM")));
                        newItem.setSector(String.valueOf(item.get("SECT_TP_NM")));
                        newItem.setCreatedDate(LocalDateTime.now());
                        return newItem;
                    }
                    return null;
                })
                // null이 아닌(신규 생성된) 객체만 필터링한다.
                .filter(Objects::nonNull)
                // Repository를 통해 DB에 저장한다.
                .forEach(itemMstRepository::save);
    }

    /**
     * 특정 시장 카테고리(KOSPI, KOSDAQ 등)에 해당하는 종목 목록을 DB에서 조회하는 메서드이다.
     * 화면 표시를 위해 순번(no)을 포함한 Map 리스트 형태로 변환하여 반환한다.
     */
    public List<Map<String, Object>> getItems(String mrktCtg) {
        AtomicInteger cnt = new AtomicInteger(0);
        List<ItemMst> items = itemMstRepository.findByMarketItems(mrktCtg);
        
        return items.stream()
                .map(item -> {
                    Map<String, Object> itemMap = new HashMap<>();
                    itemMap.put("srtnCd", item.getItemCd());
                    itemMap.put("mrktCtg", item.getMrktCtg());
                    itemMap.put("itmsNm", item.getItmsNm());
                    itemMap.put("corpNm", item.getCorpNm());
                    itemMap.put("no", cnt.incrementAndGet());
                    return itemMap;
                })
                .collect(Collectors.toList());

    }
}