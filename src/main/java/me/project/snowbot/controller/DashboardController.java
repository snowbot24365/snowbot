package me.project.snowbot.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.*;
import me.project.snowbot.service.DashboardService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 통합 대시보드 컨트롤러
 */
@Slf4j
@Controller
@RequestMapping("/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final DashboardService dashboardService;

    /**
     * 대시보드 메인 페이지
     */
    @GetMapping
    public String dashboard(Model model) {
        try {
            DashboardDto dashboardData = dashboardService.getDashboardData();
            model.addAttribute("dashboard", dashboardData);
            return "dashboard";
        } catch (Exception e) {
            log.error("대시보드 데이터 조회 중 오류 발생", e);
            model.addAttribute("error", "데이터를 불러오는 중 오류가 발생했습니다: " + e.getMessage());
            return "error";
        }
    }

    /**
     * REST API - 매수 대상 종목 조회
     */
    @GetMapping("/api/scoring-results")
    @ResponseBody
    public List<ScoringResultDto> getScoringResults(@RequestParam(required = false) String date) {
        return dashboardService.getScoringResults(date != null ? date : me.project.snowbot.util.CustomDateUtils.getToday());
    }

    /**
     * REST API - 분할 매수 진행 종목 조회
     */
    @GetMapping("/api/buying-processes")
    @ResponseBody
    public List<BuyingProcessDto> getBuyingProcesses(@RequestParam(required = false) String date) {
        return dashboardService.getBuyingProcesses(date != null ? date : me.project.snowbot.util.CustomDateUtils.getToday());
    }

    /**
     * REST API - 보유 현황 조회
     */
    @GetMapping("/api/portfolios")
    @ResponseBody
    public List<PortfolioDto> getPortfolios(@RequestParam(required = false) String date) {
        return dashboardService.getPortfolios(date != null ? date : me.project.snowbot.util.CustomDateUtils.getToday());
    }

    /**
     * REST API - 트레이딩 설정 조회
     */
    @GetMapping("/api/settings")
    @ResponseBody
    public TradingSettingsDto getSettings() {
        return dashboardService.getTradingSettings();
    }

    /**
     * REST API - 전체 대시보드 데이터 조회
     */
    @GetMapping("/api/data")
    @ResponseBody
    public DashboardDto getDashboardData() {
        return dashboardService.getDashboardData();
    }
}
