package me.project.snowbot.controller;

import java.util.List;
import java.util.concurrent.CompletableFuture;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.IndexData;
import me.project.snowbot.service.BalanceSheetService;
import me.project.snowbot.service.EtcSheetService;
import me.project.snowbot.service.FinancialSheetService;
import me.project.snowbot.service.IncomeSheetService;
import me.project.snowbot.service.ItemEquityService;
import me.project.snowbot.service.ItemPriceService;
import me.project.snowbot.service.KisService;
import me.project.snowbot.service.ProfitSheetService;

/**
 * 주식 종목(Item Equity) 관련 정보에 대한 외부 API 요청을 처리하는 컨트롤러 클래스이다.
 * <p>
 * `/item-service` 기본 경로 하위의 엔드포인트들을 관리하며,
 * 외부 KIS API 연동 서비스(`KisService`)와 내부 DB 서비스(`ItemEquityService`)를 연결하는 역할을 수행한다.
 * `@RestController`이므로 데이터(JSON 등)를 직접 반환한다.
 * </p>
 */
@Slf4j
@RequiredArgsConstructor
@RequestMapping("/item-service")
@RestController
public class ApiController {

    /** 내부 DB 조작을 위한 서비스이다. */
    private final ItemEquityService itemEquityService;
    /** 외부 KIS API 호출을 위한 서비스이다. */
    private final KisService kisService;

    /**
     * 외부 KIS API에서 특정 종목의 주식 정보를 조회하여 내부 데이터베이스에 저장(또는 갱신)하는 엔드포인트이다.
     * <p>
     * HTTP GET 요청으로 `/item-service/addEquities/{id}` 경로로 호출된다.
     * 1. `KisService`를 통해 입력받은 ID에 해당하는 최신 주식 정보를 가져온다.
     * 2. `ItemEquityService`를 통해 가져온 정보를 DB에 저장한다.
     * </p>
     * <p>
     * 반환 타입이 `CompletableFuture`로 선언되어 비동기 처리를 지원할 수 있는 구조이나,
     * 현재 구현에서는 데이터 로딩 및 저장이 동기적으로 완료된 후 결과 메시지를 즉시 반환한다.
     * </p>
     *
     * @param id URL 경로변수(`@PathVariable`)로 전달받은 종목 코드(예: 단축코드)이다.
     * @return 처리 결과 메시지("handleInertEquities")를 포함하는 완료된 `CompletableFuture` 객체이다.
     * @throws Exception API 호출이나 DB 작업 중 예기치 않은 오류 발생 시 예외를 던진다.
     */
    @GetMapping("/addEquities/{id}")
    public CompletableFuture<String> handleInsertEquities(@PathVariable("id") String id) throws Exception {
        // KIS API를 호출하여 데이터를 가져온 후, DB 서비스를 통해 저장한다.
        // ("admin"은 하드코딩된 멤버 ID 예시로 보인다.)
        itemEquityService.insert(id, kisService.getEquities(id));

        // 처리가 완료되었음을 알리는 메시지를 담아 Future를 반환한다.
        return CompletableFuture.completedFuture("handleInertEquities");
    }

    private final BalanceSheetService balanceSheetService;

    /**
     * KIS API를 통해 특정 종목의 대차대조표 정보를 조회하여 내부 DB에 저장하는 엔드포인트이다.
     * <p>
     * HTTP GET 방식으로 `/addBalance/{id}/{cl}` 경로로 요청을 받는다.
     * 1. `kisService.getSheets("B", id, cl)`을 호출하여 외부 API로부터 대차대조표("B") 데이터를 가져온다.
     * 2. `balanceSheetService.insert(id, cl, ...)`를 호출하여 가져온 데이터를 DB에 저장(또는 갱신)한다.
     * </p>
     *
     * @param id URL 경로변수(`@PathVariable`)로 전달받은 종목 코드이다. (예: "A005930")
     * @param cl URL 경로변수(`@PathVariable`)로 전달받은 결산 주기 코드이다. (0: 연간, 1: 분기)
     * @return 처리 결과 메시지를 담은 완료된 `CompletableFuture` 객체이다.
     * @throws Exception API 호출 또는 DB 작업 중 예기치 않은 오류가 발생하면 예외를 던진다.
     */
    @GetMapping("/addBalance/{id}/{cl}")
    public CompletableFuture<String> handleInsertBalanceSheet(@PathVariable("id") String id, @PathVariable("cl") String cl) throws Exception {
        // KIS API 서비스에서 대차대조표("B") 데이터를 조회한 후,
        // 대차대조표 서비스의 삽입 로직에 전달하여 DB에 저장한다.
        balanceSheetService.insert(id, cl, kisService.getSheets("B", id, cl));

        // 비동기 처리를 지원하는 구조이지만, 현재 구현에서는 동기적 작업 완료 후 즉시 결과를 반환한다.
        return CompletableFuture.completedFuture("handleInsertBalanceSheet " + cl);
    }

    private final IncomeSheetService incomeSheetService;

    /**
     * KIS API를 통해 특정 종목의 손익계산서(Income Sheet) 정보를 조회하여 내부 DB에 저장하는 엔드포인트이다.
     * <p>
     * HTTP GET 방식으로 `/addIncome/{id}/{cl}` 경로로 요청을 받는다.
     * 1. `kisService.getSheets("I", id, cl)`을 호출하여 외부 API로부터 손익계산서("I") 데이터를 가져온다.
     * 2. `incomeSheetService.insert(id, cl, ...)`를 호출하여 가져온 데이터를 DB에 저장(또는 갱신)한다.
     * </p>
     * <p>
     * 반환 타입이 `CompletableFuture`로 선언되어 비동기 처리를 지원할 수 있는 구조이나,
     * 현재 구현에서는 데이터 로딩 및 저장이 동기적으로 완료된 후 결과 메시지를 즉시 반환한다.
     * </p>
     *
     * @param id URL 경로변수(`@PathVariable`)로 전달받은 종목 코드이다. (예: "A005930")
     * @param cl URL 경로변수(`@PathVariable`)로 전달받은 재무제표 구분 코드이다. (예: "0": 연간, "1": 분기)
     * @return 처리 결과 메시지를 담은 완료된 `CompletableFuture` 객체이다.
     * @throws Exception API 호출이나 DB 작업 중 예기치 않은 오류 발생 시 예외를 던진다.
     */
    @GetMapping("/addIncome/{id}/{cl}")
    public CompletableFuture<String> handleInsertIncomeSheet(@PathVariable("id") String id, @PathVariable("cl") String cl) throws Exception {
        // KIS API 서비스에서 손익계산서("I") 데이터를 조회한 후,
        // 손익계산서 서비스의 삽입 로직에 전달하여 DB에 저장한다.
        incomeSheetService.insert(id, cl, kisService.getSheets("I", id, cl));

        // 처리가 완료되었음을 알리는 메시지를 담아 Future를 반환한다.
        return CompletableFuture.completedFuture("handleInsertIncomeSheet" + cl);
    }

    private final FinancialSheetService financialSheetService;

    /**
     * 특정 종목의 재무제표(Financial Sheet) 데이터를 수집하여 DB에 적재하는 API 엔드포인트이다.
     * 외부 API(KIS)를 통해 데이터를 조회하고, FinancialSheetService를 통해 저장한다.
     *
     * @param id 종목 코드
     * @param cl 재무제표 구분 (예: 연간, 분기 등)
     * @return 처리 완료 메시지를 포함한 비동기 결과 객체(CompletableFuture)이다.
     * @throws Exception 데이터 수집 또는 저장 중 오류가 발생할 경우 예외를 던진다.
     */
    @GetMapping("/addFinancial/{id}/{cl}")
    public CompletableFuture<String> handleInsertFinancialSheet(@PathVariable("id") String id, @PathVariable("cl") String cl) throws Exception {
        // KIS 서비스로부터 재무제표 데이터("F")를 조회하고, 서비스 로직을 통해 DB에 저장(Insert/Update)한다.
        financialSheetService.insert(id, cl, kisService.getSheets("F", id, cl));
        
        // 작업 완료 후 성공 메시지를 포함한 Future 객체를 반환한다.
        return CompletableFuture.completedFuture("handleInsertFinancialSheet" + cl);
    }

    private final ProfitSheetService profitSheetService;

    /**
     * 특정 종목의 수익성 지표(Profit Sheet) 데이터를 수집하여 DB에 적재하는 API 엔드포인트이다.
     * 외부 API(KIS)를 통해 데이터를 조회하고, ProfitSheetService를 통해 저장한다.
     *
     * @param id 종목 코드
     * @param cl 재무제표 구분 (예: 연간, 분기 등)
     * @return 처리 완료 메시지를 포함한 비동기 결과 객체(CompletableFuture)이다.
     * @throws Exception 데이터 수집 또는 저장 중 오류가 발생할 경우 예외를 던진다.
     */
    @GetMapping("/addProfit/{id}/{cl}")
    public CompletableFuture<String> handleInsertProfitSheet(@PathVariable("id") String id, @PathVariable("cl") String cl) throws Exception {
        // KIS 서비스로부터 수익성 지표 데이터("P")를 조회하고, 서비스 로직을 통해 DB에 저장(Insert/Update)한다.
        profitSheetService.insert(id, cl, kisService.getSheets("P", id, cl));
        
        // 작업 완료 후 성공 메시지를 포함한 Future 객체를 반환한다.
        return CompletableFuture.completedFuture("handleInsertProfitSheet" + cl);
    }

    private final EtcSheetService etcSheetService;

    /**
     * 특정 종목의 기타 재무 지표(Etc Sheet) 데이터를 수집하여 DB에 적재하는 API 엔드포인트이다.
     * 외부 API(KIS)를 통해 데이터를 조회하고, EtcSheetService를 통해 저장한다.
     *
     * @param id 종목 코드
     * @param cl 재무제표 구분 (예: 연간, 분기 등)
     * @return 처리 완료 메시지를 포함한 비동기 결과 객체(CompletableFuture)이다.
     * @throws Exception 데이터 수집 또는 저장 중 오류가 발생할 경우 예외를 던진다.
     */
    @GetMapping("/addEtc/{id}/{cl}")
    public CompletableFuture<String> handleInsertEtcSheet(@PathVariable("id") String id, @PathVariable("cl") String cl) throws Exception {
        // KIS 서비스로부터 기타 재무 지표 데이터("E")를 조회하고, 서비스 로직을 통해 DB에 저장(Insert/Update)한다.
        etcSheetService.insert(id, cl, kisService.getSheets("E", id, cl));
        
        // 작업 완료 후 성공 메시지를 포함한 Future 객체를 반환한다.
        return CompletableFuture.completedFuture("handleInsertEtcSheet" + cl);
    }

    private final ItemPriceService itemPriceService;

    /**
     * 특정 종목(id)의 최신 시세 데이터를 외부 API로부터 조회하여 데이터베이스에 저장하는 엔드포인트이다.
     * 비동기 처리 응답 규격을 위해 CompletableFuture를 반환한다.
     *
     * @param id 조회 및 저장할 종목 코드이다.
     * @return 작업 완료 상태를 포함한 Future 객체이다.
     * @throws Exception 처리 중 발생할 수 있는 예외를 던진다.
     */
    @GetMapping("/addPrice/{id}")
    public CompletableFuture<String> handleInsertPrice(@PathVariable("id") String id) throws Exception {
        // 1. 외부 서비스(KIS)를 통해 해당 종목의 당일(또는 최신) 차트 데이터를 조회한다.
        // (두 번째 인자 true는 당일 데이터 조회를 의미한다.)
        List<IndexData> indexDataList = kisService.getItemChartPrice(id, true);

        // 2. 조회된 데이터 리스트를 순회하며, 각 데이터를 시세 서비스(ItemPriceService)를 통해 DB에 적재한다.
        indexDataList.forEach(indexData -> itemPriceService.insert(id, indexData));

        // 3. 작업 완료 메시지를 포함한 CompletableFuture 객체를 생성하여 반환한다.
        return CompletableFuture.completedFuture("handleInsertPrice");
    }

}