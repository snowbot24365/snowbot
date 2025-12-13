package me.project.snowbot.controller;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.service.ItemMstService;
import me.project.snowbot.service.SlackService;

@Slf4j
@RequiredArgsConstructor
@Controller
@RequestMapping("/item-mst")
public class ItemMstController {
    
    private final ItemMstService itemMstService;
    private final SlackService slackService;
    
    /**
     * 매월 1일 오전 6시에 자동으로 실행되어 종목 정보를 갱신한다.
     * 공공데이터포털에서 종목 정보를 조회한 후 중복을 제거하고 DB에 저장한다.
     */
    @Scheduled(cron = "0 0 6 1 * *", zone = "Asia/Seoul")   // 매월 1일 오전 6시 실행
    @GetMapping("/items/get")
    public void insertItems() throws Exception {
        log.info("Execute insertItems Start");
        slackService.sendMessage("Execute insertItems Start");
        
        // 종목 정보를 조회하여 종목코드 기준으로 중복 제거 후 DB에 저장
        itemMstService.insert(removeDuplicates(itemMstService.getItemsInfo("KOSPI"), "ISU_SRT_CD"));
        itemMstService.insert(removeDuplicates(itemMstService.getItemsInfo("KOSDAQ"), "ISU_SRT_CD"));
        
        log.info("Execute insertItems End");
        slackService.sendMessage("Execute insertItems End");
    }
    
    /**
     * 리스트에서 특정 키 값을 기준으로 중복된 항목을 제거한다.
     * 
     * @param list 중복을 제거할 Map 리스트
     * @param keyToCheck 중복 검사 기준이 되는 키 (예: "srtnCd")
     * @return 중복이 제거된 Map 리스트
     */
    public static List<Map<String, String>> removeDuplicates(List<Map<String, String>> list, String keyToCheck) {
        // 이미 확인한 키 값을 저장하는 Set
        HashSet<Object> seen = new HashSet<>();
        
        // Stream을 사용해 중복되지 않은 항목만 필터링
        return list.stream()
                .filter(item -> seen.add(item.get(keyToCheck)))  // seen에 추가되면 true(유지), 이미 있으면 false(제거)
                .collect(Collectors.toList());
    }

    /**
     * URL 경로로 전달받은 시장 구분(mrktCtg)에 해당하는 종목 리스트를 조회하여 화면으로 전달하는 컨트롤러 메서드이다.
     * 예: /items/KOSPI 요청 시 KOSPI 종목들을 조회한다.
     */
    @GetMapping("/items/{mrktCtg}")
    public String getItems(@PathVariable("mrktCtg") String mrktCtg, Model model) {

        // 서비스 계층을 호출하여 해당 시장의 종목 데이터를 조회하고, 뷰(View)에서 사용할 수 있도록 Model 객체에 'itemList'라는 이름으로 담는다.
        model.addAttribute("itemList", itemMstService.getItems(mrktCtg));

        // 데이터를 출력할 뷰 템플릿(HTML)의 경로(stock/items)를 반환한다.
        return "stock/items";
    }
}