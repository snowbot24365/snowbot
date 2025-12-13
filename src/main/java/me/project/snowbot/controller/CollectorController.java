package me.project.snowbot.controller;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CompletableFuture;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.IndexData;
import me.project.snowbot.entity.ItemPrice;
import me.project.snowbot.service.ItemMstService;
import me.project.snowbot.service.ItemPriceService;
import me.project.snowbot.service.KisService;
import me.project.snowbot.service.SlackService;
import me.project.snowbot.util.CustomDateUtils;

/**
 * 주식 데이터 수집을 담당하는 컨트롤러이다.
 * 정해진 시간에 스케줄러를 통해 KOSPI 및 KOSDAQ 전 종목의 시세와 재무 정보를 수집하여 DB에 저장한다.
 */
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/collector")
public class CollectorController {
    private final KisService kisService;
    private final ItemPriceService itemPriceService;
    private final ApiController apiController;
    private final ItemMstService itemMstService;
    private final SlackService slackService;

    /**
     * 매일 17시(오후 5시)에 KOSPI 시장의 데이터를 수집하는 스케줄러 메서드이다.
     * 작업 시작과 종료 시 슬랙으로 알림을 발송한다.
     */
    @Scheduled(cron = "0 0 17 * * *", zone = "Asia/Seoul") // Executes at 17:00 PM every day
    @GetMapping("/addkospi")
    public ResponseEntity<String> insertEquitiesKospi() {
        log.info("Execute insertEquities Start");
        slackService.sendMessage("Execute insertEquitiesKospi Start");
        
        // KOSPI 시장 종목 수집을 시작한다.
        insertEquitiesByMarket("KOSPI");
        
        log.info("Execute insertEquities End");
        slackService.sendMessage("Execute insertEquitiesKospi End");
        return ResponseEntity.status(HttpStatus.OK).body("Execute insertEquitiesKospi End");
    }

    /**
     * 매일 16시(오후 4시)에 KOSDAQ 시장의 데이터를 수집하는 스케줄러 메서드이다.
     */
    @Scheduled(cron = "0 0 16 * * *", zone = "Asia/Seoul") // Executes at 16:00 PM every day
    @GetMapping("/addkosdaq")
    public ResponseEntity<String> insertEquitiesKosdaq() {
        log.info("Execute insertEquities Start");
        slackService.sendMessage("Execute insertEquitiesKosdaq Start");
        
        // KOSDAQ 시장 종목 수집을 시작한다.
        insertEquitiesByMarket("KOSDAQ");
        
        log.info("Execute insertEquities End");
        slackService.sendMessage("Execute insertEquitiesKosdaq End");
        return ResponseEntity.status(HttpStatus.OK).body("Execute insertEquitiesKosdaq End");
    }

    /**
     * 특정 시장(KOSPI, KOSDAQ)의 전체 종목 리스트를 가져와 순차적으로 데이터를 수집하는 메서드이다.
     *
     * @param market 수집할 시장 구분 코드이다.
     */
    private void insertEquitiesByMarket(String market) {
        itemMstService.getItems(market).stream()
                .map(item -> String.valueOf(item.get("srtnCd"))) // 종목 코드(단축 코드)를 추출한다.
                .forEach(item -> {
                    // 1. 해당 종목의 기본 정보 및 시세, 재무 데이터를 수집한다.
                    insertEquities(item);
                    // 2. 수집된 시세 데이터를 바탕으로 이동평균선을 계산하여 업데이트한다.
                    addMas(item);
                });
    }

    /**
     * 개별 종목(id)에 대한 시세 및 재무 데이터를 수집하여 저장하는 핵심 로직이다.
     * 시세 데이터는 동기적으로, 재무 데이터는 비동기적으로 처리하여 성능을 최적화한다.
     *
     * @param id 종목 코드이다.
     */
    private void insertEquities(String id) {
        try {
            boolean bInsert;
            boolean bToday = false;
            
            // 1. DB에 해당 종목의 데이터가 존재하는지 확인한다.
            List<ItemPrice> itemPriceList = itemPriceService.findById(id);
            
            if (itemPriceList != null && !itemPriceList.isEmpty()) {
                // 데이터가 존재한다면, 오늘 날짜의 데이터가 누락되었는지 확인한다.
                // 오늘 데이터가 없으면 수집 대상(bInsert=true)이 된다.
                bInsert = itemPriceService.findByIdDate(id, CustomDateUtils.getStringToday()) == null;
                bToday = bInsert; // 기존 데이터가 있으므로 오늘치만 추가하면 된다.
            } else {
                // 데이터가 아예 없다면 전체 히스토리를 수집해야 한다.
                bInsert = true;
            }

            if (bInsert) {
                // [Price 수집]
                // KIS 서비스를 통해 시세 차트 데이터를 가져온다. (bToday가 false면 과거 데이터까지 포함)
                // 1회 최대 100건 단위로 처리된다.
                List<IndexData> indexDataList = kisService.getItemChartPrice(id, bToday);
                indexDataList.forEach(indexData -> itemPriceService.insert(id, indexData));

                // [재무 데이터 비동기 수집]
                // 여러 외부 API 호출을 병렬로 처리하여 수집 시간을 단축한다.
                
                // 1. 주식 기본 정보(Equities) 수집 작업이다.
                CompletableFuture<String> equitiesFuture = apiController.handleInsertEquities(id);

                // 2. 재무제표 수집 작업이다. (참고: 모의투자는 지원하지 않을 수 있음)
                // 대차대조표 (연간/분기 등 구분 코드 "0", "1"로 각각 요청)
                CompletableFuture<String> balanceSheet0Future = apiController.handleInsertBalanceSheet(id, "0");
                CompletableFuture<String> balanceSheet1Future = apiController.handleInsertBalanceSheet(id, "1");

                // 손익계산서
                CompletableFuture<String> incomeSheet0Future = apiController.handleInsertIncomeSheet(id, "0");
                CompletableFuture<String> incomeSheet1Future = apiController.handleInsertIncomeSheet(id, "1");

                // 재무비율
                CompletableFuture<String> financialSheet0Future = apiController.handleInsertFinancialSheet(id, "0");
                CompletableFuture<String> financialSheet1Future = apiController.handleInsertFinancialSheet(id, "1");

                // 수익성비율
                CompletableFuture<String> profitSheet0Future = apiController.handleInsertProfitSheet(id, "0");
                CompletableFuture<String> profitSheet1Future = apiController.handleInsertProfitSheet(id, "1");

                // 기타주요비율
                CompletableFuture<String> etcSheet0Future = apiController.handleInsertEtcSheet(id, "0");
                CompletableFuture<String> etcSheet1Future = apiController.handleInsertEtcSheet(id, "1");

                // 3. 모든 비동기 작업(CompletableFuture)이 완료될 때까지 대기한다. (Blocking)
                CompletableFuture.allOf(
                        equitiesFuture,
                        balanceSheet0Future, balanceSheet1Future,
                        incomeSheet0Future, incomeSheet1Future,
                        financialSheet0Future, financialSheet1Future,
                        profitSheet0Future, profitSheet1Future,
                        etcSheet0Future, etcSheet1Future
                ).join();

            } else {
                log.info("Existing Equities : " + id);
            }
        } catch (IOException e) {
            // IO 예외 발생 시(예: 토큰 만료 등) 처리를 수행한다. 현재는 주석 처리되어 있다.
            //accessTokenManager.generateAccessToken();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * 특정 종목의 이동평균선(MA) 데이터를 계산하여 업데이트하는 메서드이다.
     *
     * @param id 종목 코드이다.
     */
    private void addMas(String id) {
        List<ItemPrice> itemPriceList = itemPriceService.findById(id);
        itemPriceService.addMa(itemPriceList);
    }
}