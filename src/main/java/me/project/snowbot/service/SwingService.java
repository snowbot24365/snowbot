package me.project.snowbot.service;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.SwingScore;
import me.project.snowbot.entity.SwingScorePK;
import me.project.snowbot.repository.FinancialSheetRepository;
import me.project.snowbot.repository.SwingScoreRepository;

/**
 * 스윙 트레이딩 전략에 따른 종목별 평가 점수(SwingScore)를 관리하고 조회하는 서비스 클래스이다.
 * 재무제표 필터링 및 각 종목의 점수 계산 결과를 저장하는 역할을 수행한다.
 */
@Slf4j
@RequiredArgsConstructor
@Service
public class SwingService {
    private final FinancialSheetRepository financialSheetRepository;
    private final SwingScoreRepository swingScoreRepository;

    /**
     * 특정 재무 조건(예: 흑자 지속, 부채비율 등)을 만족하는 재무제표 데이터를 필터링하여 조회한다.
     * 반환값은 종목 코드와 관련 재무 정보를 포함한 객체 배열 리스트이다.
     */
    public List<Object[]> findFilteredFinancialSheets() {
        return financialSheetRepository.findFilteredFinancialSheets();
    }

    /**
     * 특정 기준 날짜(date)에 해당하는 모든 종목의 스윙 점수 리스트를 조회한다.
     */
    public List<SwingScore> findByDate(String date) {
        return swingScoreRepository.findByDate(date);
    }

    /**
     * 기준 날짜와 종목 코드를 복합키로 사용하여 특정 종목의 점수 데이터를 단건 조회한다.
     */
    public SwingScore findByKey(String date, String itemCd) {
        return swingScoreRepository.findByKey(itemCd, date);
    }

    /**
     * 특정 종목에 대해 가장 최근에 저장된 스윙 점수 데이터를 조회한다.
     */
    public SwingScore findByLastData(String itemCd) {
        return swingScoreRepository.findByLastData(itemCd);
    }

    /**
     * 종목의 다양한 평가 항목 점수를 입력받아 DB에 저장하거나 업데이트한다.
     * 이미 데이터가 존재하면 업데이트하고, 없으면 새로 생성하는 Upsert 로직을 수행한다.
     *
     * @param id 종목 코드이다.
     * @param date 기준 날짜이다.
     * @param sheetScore 재무 점수이다.
     * @param trendScore 추세 점수이다.
     * @param priceScore 가격 위치 점수이다.
     * @param kpiScore KPI 지표 점수이다.
     * @param buyScore 매수 신호 점수이다.
     * @param avlsScore 거래량/변동성 분석 점수이다.
     * @param perScore 주가수익비율(PER) 점수이다.
     * @param pbrScore 주가순자산비율(PBR) 점수이다.
     * @param totScore 종합 점수이다.
     */
    public void save(
            String id, String date, int sheetScore, int trendScore, int priceScore, int kpiScore, int buyScore,
            int avlsScore, int perScore, int pbrScore, int totScore
    ) {
        // 1. 해당 날짜와 종목 코드에 대한 점수 데이터가 존재하는지 확인한다.
        // 데이터가 없으면 새로운 키(PK)와 엔티티 객체를 생성하여 반환한다.
        SwingScore swingScore = Optional.ofNullable(swingScoreRepository.findByKey(id, date))
                .orElseGet(() -> {
                    SwingScorePK swingScorePK = new SwingScorePK();
                    swingScorePK.setItem_cd(id);
                    swingScorePK.setStckBsopDate(date);
                    SwingScore newSwingScore = new SwingScore();
                    newSwingScore.setId(swingScorePK);
                    return newSwingScore;
                });

        // 2. 각 평가 항목별 점수를 설정한다.
        swingScore.setSheetScore(sheetScore);
        swingScore.setTrendScore(trendScore);
        swingScore.setPriceScore(priceScore);
        swingScore.setKpiScore(kpiScore);
        swingScore.setBuyScore(buyScore);
        swingScore.setAvlsScore(avlsScore);
        swingScore.setPerScore(perScore);
        swingScore.setPbrScore(pbrScore);
        swingScore.setTotalScore(totScore);

        // 3. 최종적으로 엔티티를 저장한다.
        swingScoreRepository.save(swingScore);
    }
}