package me.project.snowbot.service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.SwingData;
import me.project.snowbot.entity.ItemPrice;
import me.project.snowbot.util.CustomDateUtils;

/**
 * 스윙(Swing) 트레이딩 전략을 기반으로 전체 종목의 점수를 계산하고,
 * 유망 종목을 선별(Filtering)하여 저장하는 핵심 비즈니스 로직을 담당하는 서비스 클래스이다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ScorerService {

    private final ItemPriceService itemPriceService;
    private final ItemTradeInfoService itemTradeInfoService;
    private final IncomeSheetService incomeSheetService;
    private final SwingService swingService;

    // --- 점수 임계값 및 상수 정의 ---
    /** 재무 건전성 최소 합격 점수이다. */
    private static final int MIN_SHEET_SCORE = 3;
    /** 가격 위치 최소 합격 점수이다. */
    private static final int MIN_PRICE_SCORE = 0;
    /** 추세(Trend) 최소 합격 점수이다. */
    private static final int MIN_TREND_SCORE = 3;
    /** 시가총액 규모 최소 합격 점수이다. */
    private static final int MIN_AVLS_SCORE = 3;
    /** 최종 선정 되기 위한 총점 기준값이다. */
    private static final int TOTAL_SCORE_THRESHOLD = 30;
    
    private static final String SWING_TYPE = "SW";
    private static final String YES = "Y";

    /**
     * 전체 종목의 재무 및 시세 데이터를 조회하여 채점(Scoring) 프로세스를 실행하는 메인 메서드이다.
     * 점수 계산 후 기준을 통과한 종목은 DB에 매매 대상(ItemTradeInfo)으로 저장한다.
     */
    @Transactional
    public void executeSwingScoring() {
        String date = CustomDateUtils.getStringToday();

        // 1. 재무제표 필터링을 거친 분석 대상 데이터를 조회하고, 계산에 용이한 DTO로 변환한다.
        List<SwingData> swingDataList = swingService.findFilteredFinancialSheets().stream()
                .map(this::mapToSwingData)
                .collect(Collectors.toList());

        // 2. 각 종목별로 상세 점수 계산 및 필터링 로직을 수행한다.
        swingDataList.forEach(swingData -> processSwingData(swingData, date));
    }

    /**
     * 개별 종목에 대해 재무, 가격, 추세, 수급 등 항목별 점수를 계산한다.
     * 중간 단계에서 기준 점수에 미달하면 즉시 리턴하여 불필요한 연산을 방지한다.
     *
     * @param swingData 분석 대상 종목 데이터
     * @param date 기준 날짜
     */
    private void processSwingData(SwingData swingData, String date) {
        // 1. 재무 점수 평가 (기준 미달 시 탈락)
        int sheetScore = calculateSheetScore(swingData);
        if (sheetScore < MIN_SHEET_SCORE) return;

        // 2. 가격 위치 점수 평가 (기준 미달 시 탈락)
        int priceScore = calculatePriceScore(swingData);
        if (priceScore < MIN_PRICE_SCORE) return;

        // 3. 이동평균선 추세 점수 평가 (기준 미달 시 탈락)
        int trendScore = calculateTrendScore(swingData);
        if (trendScore < MIN_TREND_SCORE) return;

        // 4. 시가총액 규모 점수 평가 (기준 미달 시 탈락 - 너무 작은 소형주 등 제외 목적)
        int avlsScore = calculateAvlsScore(swingData);
        if (avlsScore < MIN_AVLS_SCORE) return;

        // 5. 기타 보조 지표 점수 계산
        int buyScore = calculateBuyScore(swingData);       // 수급(외인/기관)
        int perScore = calculatePerScore(swingData);       // PER 밸류에이션
        int pbrScore = calculatePbrScore(swingData);       // PBR 밸류에이션
        
        // 기술적 지표(RSI, OBV) 점수 계산 (DB 추가 조회가 발생함에 유의한다)
        int kpiScore = calculateKPIScore(swingData.getItemCd()); 

        // 6. 최종 총점 계산
        int totScore = sheetScore + trendScore + priceScore + buyScore + kpiScore + avlsScore + perScore + pbrScore;

        // 7. 총점이 임계값을 넘을 경우, 유망 종목으로 판단하여 결과를 저장한다.
        if (totScore > TOTAL_SCORE_THRESHOLD) {
            log.info("Swing Item Found: {} ({}), Score: {}", swingData.getItmsNm(), swingData.getItemCd(), totScore);
            
            // 상세 점수 내역 저장
            swingService.save(swingData.getItemCd(), date, sheetScore, trendScore, priceScore, kpiScore, buyScore, avlsScore, perScore, pbrScore, totScore);
            // 매매 대상 플래그 업데이트 (ItemTradeInfo)
            itemTradeInfoService.saveItemTradeInfoByLast(swingData.getItemCd(), date, YES, SWING_TYPE, "swing target");
        }
    }

    // --- 점수 계산 로직 (Scoring Logic) ---

    /**
     * 기업의 성장성, 수익성, 안정성을 나타내는 재무 지표를 기반으로 점수를 계산한다.
     */
    private int calculateSheetScore(SwingData d) {
        int score = 0;
        if (getValue(d.getGrs()) > 10) score++;              // 매출액 증가율 > 10%
        if (getValue(d.getBsopPrfiInrt()) > 10) score++;     // 영업이익률 > 10%
        if (getValue(d.getRsrvRate()) > 500) score++;        // 유보율 > 500% (현금 흐름 양호)
        if (getValue(d.getLbltRate()) > 50) score++;         // 부채비율 조건 (주의: 보통 낮은 것이 좋으나 전략에 따라 다름)
        if (getThtrNtin(d.getItemCd()) > 0) score++;         // 당기순이익 흑자 여부
        return score;
    }

    /**
     * 현재 주가가 연중 최고가/최저가 대비 매력적인 위치에 있는지 평가한다.
     * 고점 대비 많이 하락했으면 가산점, 저점 대비 너무 많이 올랐으면 감점한다.
     */
    private int calculatePriceScore(SwingData d) {
        int score = calculateHighPriceScore(getValue(d.getDryyHgprVrssPrprRate()));
        score -= calculateLowPricePenalty(getValue(d.getDryyLwprVrssPrprRate()));
        return Math.max(0, score); // 점수는 0보다 작아지지 않게 한다.
    }

    // 연중 최고가 대비 하락률에 따른 가산점 계산
    private int calculateHighPriceScore(double rate) {
        if (rate < -30) return 5; // 30% 이상 하락 (과대 낙폭)
        if (rate < -20) return 4;
        if (rate < -10) return 3;
        if (rate < -5) return 2;
        return rate < 0 ? 1 : 0;
    }

    // 연중 최저가 대비 상승률에 따른 페널티 계산 (이미 너무 급등한 종목 제외)
    private int calculateLowPricePenalty(double rate) {
        if (rate > 30) return 3; // 30% 이상 급등
        if (rate > 20) return 2;
        return rate > 10 ? 1 : 0;
    }

    /**
     * 이동평균선(MA) 배열 상태를 분석하여 상승 추세 초입인지 평가한다.
     */
    private int calculateTrendScore(SwingData d) {
        int score = 0;
        double close = getValue(d.getStckClpr());
        double ma5 = getValue(d.getMa5());
        double ma20 = getValue(d.getMa20());
        double ma60 = getValue(d.getMa60());

        if (ma5 == 0 || ma20 == 0 || ma60 == 0) return 0;

        if (ma60 > ma20) score += 2;   // 60일선이 20일선보다 위에 있음 (눌림목 혹은 조정 구간 가능성)
        if (close >= ma20) score += 2; // 주가가 20일 생명선을 지지하고 있음
        if (close >= ma5) score += 1;  // 주가가 5일선 위에 있어 단기 탄력이 좋음
        return score;
    }

    /**
     * 외국인과 기관의 수급 동향(순매수 비중, 보유율)을 분석하여 점수를 매긴다.
     */
    private int calculateBuyScore(SwingData d) {
        // 거래량 대비 순매수 비율 계산
        double volRate = Math.max(
            calculateRate(getValue(d.getFrgnNtbyQty()), d.getAcmlVol()),
            calculateRate(getValue(d.getPgtrNtbyQty()), d.getAcmlVol())
        );
        // 상장 주식 수 대비 외국인 보유율 계산
        double holdingRate = calculateRate(getValue(d.getFrgnHldnQty()), d.getLstnStcn());

        if (volRate > 10 && holdingRate > 10) return 5;
        if (volRate > 10 || holdingRate > 10) return 4;
        if (volRate > 5 && holdingRate > 5) return 3;
        return (volRate > 5 || holdingRate > 5) ? 2 : 1;
    }

    /**
     * 시가총액 규모에 따라 점수를 부여한다. (너무 작은 소형주 배제 및 대형주 선호 경향)
     */
    private int calculateAvlsScore(SwingData d) {
        double cap = getValue(d.getLstnStcn()) * d.getStckClpr();
        double BILLION = 100_000_000;

        if (cap < 100 * BILLION) return 1;  // 1000억 미만
        if (cap < 500 * BILLION) return 2;
        if (cap < 1000 * BILLION) return 3;
        if (cap < 5000 * BILLION) return 4;
        return 5;                           // 5000억 이상
    }

    /**
     * 주가수익비율(PER)을 기준으로 저평가 여부를 판단한다.
     */
    private int calculatePerScore(SwingData d) {
        double per = getValue(d.getPer());
        if (per <= 0) return 1; // 적자 기업 등
        if (per < 5) return 5;  // PER 5 미만 (극도로 저평가)
        if (per < 10) return 4;
        if (per < 15) return 3;
        if (per < 20) return 2;
        return 1;
    }

    /**
     * 주가순자산비율(PBR)을 기준으로 자산 가치 대비 저평가 여부를 판단한다.
     */
    private int calculatePbrScore(SwingData d) {
        double pbr = getValue(d.getPbr());
        if (pbr <= 0) return 1;
        if (pbr < 1) return 5;  // PBR 1 미만 (청산 가치보다 쌈)
        if (pbr < 2) return 4;
        if (pbr < 3) return 3;
        if (pbr < 4) return 2;
        return 1;
    }

    // --- 기술적 지표 (KPI: RSI, OBV) 로직 ---

    /**
     * 과거 시세 데이터를 조회하여 RSI와 OBV 보조지표 점수를 계산한다.
     */
    private int calculateKPIScore(String itemCd) {
        List<ItemPrice> prices = itemPriceService.findById(itemCd);
        int rsiScore = calculateRSI(prices, 14);
        int obvScore = calculateOBV(prices, 14);
        // 두 지표 중 하나라도 의미 있는 시그널이 나오면 추가 점수를 부여한다.
        return rsiScore + obvScore + ((rsiScore != 0 && obvScore != 0) ? 1 : 0);
    }

    /**
     * 상대강도지수(RSI)를 계산하여 과매도/과매수 구간을 판단한다.
     *
     * @param itemPriceList 과거 시세 리스트
     * @param period 계산 기간 (보통 14일)
     * @return 2(과매도-매수시그널), -2(과매수-매도시그널), 0(중립)
     */
    private int calculateRSI(List<ItemPrice> itemPriceList, int period) {
        if (itemPriceList.size() < period) return 0;
        
        try {
            double[] gains = new double[itemPriceList.size()];
            double[] losses = new double[itemPriceList.size()];

            // 전일 대비 상승분과 하락분을 계산한다.
            IntStream.range(1, itemPriceList.size()).forEach(i -> {
                double change = itemPriceList.get(i).getStck_clpr() - itemPriceList.get(i - 1).getStck_clpr();
                if (change > 0) gains[i] = change;
                else losses[i] = -change;
            });

            double averageGain = IntStream.rangeClosed(1, period).mapToDouble(i -> gains[i]).average().orElse(0);
            double averageLoss = IntStream.rangeClosed(1, period).mapToDouble(i -> losses[i]).average().orElse(0);

            // Wilder의 평활화(Smoothing) 방식을 사용하여 RSI를 계산한다.
            double rsi = 0.0;
            for (int i = period; i < itemPriceList.size(); i++) {
                averageGain = (averageGain * (period - 1) + gains[i]) / period;
                averageLoss = (averageLoss * (period - 1) + losses[i]) / period;
                double rs = (averageLoss == 0) ? 100 : averageGain / averageLoss;
                rsi = (averageLoss == 0) ? 100 : 100 - (100 / (1 + rs));
            }

            if (rsi > 70) return -2; // RSI 70 초과: 과매수 구간 (매도 관점)
            else if (rsi < 30) return 2; // RSI 30 미만: 과매도 구간 (매수 관점)
            else return 0;
        } catch (Exception e) {
            log.error("RSI Calculation Error", e);
            return 0;
        }
    }

    /**
     * 거래량 균형 지표(OBV)를 계산하여 주가 흐름의 신뢰도를 판단한다.
     *
     * @return 2(상승다이버전스), -2(하락다이버전스), 0(보합)
     */
    private int calculateOBV(List<ItemPrice> itemPriceList, int period) {
        if (itemPriceList.size() < 2) return 0;

        try {
            List<Double> obvValues = new ArrayList<>();
            double obv = 0.0;
            obvValues.add(obv);

            // 주가 상승 시 거래량 더하고, 하락 시 거래량 빼는 방식으로 누적한다.
            for (int i = 1; i < itemPriceList.size(); i++) {
                double currentClose = itemPriceList.get(i).getStck_clpr();
                double prevClose = itemPriceList.get(i - 1).getStck_clpr();
                double volume = itemPriceList.get(i).getAcml_vol();

                if (currentClose > prevClose) obv += volume;
                else if (currentClose < prevClose) obv -= volume;
                obvValues.add(obv);
            }

            if (obvValues.size() < period) return 0;

            // 기간 내 OBV 추세를 비교한다.
            double startOBV = obvValues.get(obvValues.size() - period);
            double endOBV = obvValues.get(obvValues.size() - 1);

            if (endOBV > startOBV) return 2; // OBV 상승 추세
            else if (endOBV < startOBV) return -2; // OBV 하락 추세
            else return 0;
        } catch (Exception e) {
            log.error("OBV Calculation Error", e);
            return 0;
        }
    }

    // --- 유틸리티 메서드 ---

    /**
     * 종목의 당기순이익 정보를 조회한다. 데이터가 없으면 0.0을 반환한다.
     */
    private double getThtrNtin(String itemCd) {
        return incomeSheetService.findByid(itemCd).stream()
                .findFirst()
                .map(sheet -> sheet.getThtr_ntin() != null ? sheet.getThtr_ntin().doubleValue() : 0.0)
                .orElse(0.0);
    }

    /**
     * 두 수의 비율(Percentage)을 계산한다. 분모가 0일 경우 0.0을 반환한다.
     */
    private double calculateRate(double a, double b) {
        return (b == 0) ? 0.0 : (a / b) * 100;
    }

    // Null-Safe Double 변환 (NullPointerException 방지)
    private double getValue(Double val) {
        return val == null ? 0.0 : val;
    }
    
    // Null-Safe Integer to Double 변환
    private double getValue(Integer val) {
        return val == null ? 0.0 : val.doubleValue();
    }
    
    // Null-Safe BigDecimal to Double 변환
    private double getValue(BigDecimal val) {
        return val == null ? 0.0 : val.doubleValue();
    }

    /**
     * Object 배열 형태의 쿼리 결과를 비즈니스 로직에 적합한 SwingData DTO로 매핑한다.
     */
    private SwingData mapToSwingData(Object[] row) {
        return new SwingData(
            (String) row[0], (String) row[1], (String) row[2], (String) row[3],
            (BigDecimal) row[4], (BigDecimal) row[5], (BigDecimal) row[6], (BigDecimal) row[7],
            (Integer) row[8],
            (BigDecimal) row[9], (BigDecimal) row[10],
            (BigDecimal) row[11], (BigDecimal) row[12], (BigDecimal) row[13], (BigDecimal) row[14], 
            (BigDecimal) row[15], (BigDecimal) row[16], (BigDecimal) row[17],
            (BigDecimal) row[18], (BigDecimal) row[19],
            (Integer) row[20],
            (BigDecimal) row[21], (BigDecimal) row[22], (BigDecimal) row[23], (BigDecimal) row[24],
            (BigDecimal) row[25], (BigDecimal) row[26], (BigDecimal) row[27], (BigDecimal) row[28]
        );
    }
}