package me.project.snowbot.dto;

import java.math.BigDecimal;

import lombok.Data;

/**
 * 스윙 트레이딩 분석에 필요한 종목별 핵심 데이터(시세, 재무, 수급, 이동평균선 등)를 담는 DTO(Data Transfer Object) 클래스이다.
 * 데이터베이스 조회 결과(주로 BigDecimal 타입)를 애플리케이션 로직에서 처리하기 쉬운 Double 타입으로 변환하여 관리한다.
 */
@Data
public class SwingData {
    // --- 기본 정보 ---
    /** 시장 구분이다. (예: KOSPI, KOSDAQ) */
    private String mrktCtg;
    /** 업종명이다. (예: 전기전자, 화학) */
    private String bstpKorIsnm;
    /** 종목 코드이다. */
    private String itemCd;
    /** 종목명이다. */
    private String itmsNm;

    // --- 재무 비율 정보 ---
    /** 매출액 증가율(성장성 지표)이다. */
    private Double grs;
    /** 영업이익률(수익성 지표)이다. */
    private Double bsopPrfiInrt;
    /** 유보율(안정성 지표)이다. */
    private Double rsrvRate;
    /** 부채비율(안정성 지표)이다. */
    private Double lbltRate;

    // --- 시세 및 가격 정보 ---
    /** 현재가(종가)이다. */
    private Integer stckClpr;
    /** 연중 최고가(52주 신고가)이다. */
    private Double stckDryyHgpr;
    /** 연중 최고가 대비 현재가 등락률이다. */
    private Double dryyHgprVrssPrprRate;
    /** 연중 최저가(52주 신저가)이다. */
    private Double stckDryyLwpr;
    /** 연중 최저가 대비 현재가 등락률이다. */
    private Double dryyLwprVrssPrprRate;

    // --- 이동평균선(MA) 정보 ---
    /** 5일 이동평균선 값이다. */
    private Double ma5;
    /** 10일 이동평균선 값이다. */
    private Double ma10;
    /** 20일 이동평균선 값이다. */
    private Double ma20;
    /** 30일 이동평균선 값이다. */
    private Double ma30;
    /** 60일 이동평균선 값이다. */
    private Double ma60;
    /** 120일 이동평균선 값이다. */
    private Double ma120;
    /** 240일 이동평균선 값이다. */
    private Double ma240;

    // --- 수급 및 거래량 정보 ---
    /** 외국인 순매수 수량이다. */
    private Double frgnNtbyQty;
    /** 기관(또는 프로그램) 순매수 수량이다. */
    private Double pgtrNtbyQty;
    /** 누적 거래량이다. */
    private Integer acmlVol;
    /** 외국인 보유 수량이다. */
    private Double frgnHldnQty;
    /** 상장 주식 수이다. */
    private Double lstnStcn;

    // --- 투자 지표 (Valuation) ---
    /** 주가수익비율(PER)이다. */
    private Double per;
    /** 주가순자산비율(PBR)이다. */
    private Double pbr;
    /** 주당순이익(EPS)이다. */
    private Double eps;
    /** 주당순자산가치(BPS)이다. */
    private Double bps;

    /**
     * JPQL 등의 쿼리 결과(BigDecimal)를 Double 타입으로 변환하여 초기화하는 생성자이다.
     * 숫자형 데이터의 경우 null 값이 입력되면 null로 처리하여 NullPointerException을 방지한다.
     *
     * @param mrktCtg 시장 구분
     * @param bstpKorIsnm 업종명
     * @param itemCd 종목 코드
     * @param itmsNm 종목명
     * @param grs 매출액 증가율
     * @param bsopPrfiInrt 영업이익률
     * @param rsrvRate 유보율
     * @param lbltRate 부채비율
     * @param stckClpr 현재가
     * @param stckDryyHgpr 연중 최고가
     * @param dryyHgprVrssPrprRate 최고가 대비 등락률
     * @param ma5 5일 이평선
     * @param ma10 10일 이평선
     * @param ma20 20일 이평선
     * @param ma30 30일 이평선
     * @param ma60 60일 이평선
     * @param ma120 120일 이평선
     * @param ma240 240일 이평선
     * @param frgnNtbyQty 외국인 순매수
     * @param pgtrNtbyQty 기관 순매수
     * @param acmlVol 누적 거래량
     * @param frgnHldnQty 외국인 보유 수량
     * @param lstnStcn 상장 주식 수
     * @param per PER
     * @param pbr PBR
     * @param stckDryyLwpr 연중 최저가
     * @param dryyLwprVrssPrprRate 최저가 대비 등락률
     * @param eps EPS
     * @param bps BPS
     */
    public SwingData(String mrktCtg, String bstpKorIsnm, String itemCd, String itmsNm, BigDecimal grs,
                     BigDecimal bsopPrfiInrt, BigDecimal rsrvRate, BigDecimal lbltRate, Integer stckClpr,
                     BigDecimal stckDryyHgpr, BigDecimal dryyHgprVrssPrprRate, BigDecimal ma5, BigDecimal ma10,
                     BigDecimal ma20, BigDecimal ma30, BigDecimal ma60, BigDecimal ma120, BigDecimal ma240,
                     BigDecimal frgnNtbyQty, BigDecimal pgtrNtbyQty, Integer acmlVol, BigDecimal frgnHldnQty,
                     BigDecimal lstnStcn, BigDecimal per, BigDecimal pbr, BigDecimal stckDryyLwpr, BigDecimal dryyLwprVrssPrprRate,
                     BigDecimal eps, BigDecimal bps) {
        this.mrktCtg = mrktCtg;
        this.bstpKorIsnm = bstpKorIsnm;
        this.itemCd = itemCd;
        this.itmsNm = itmsNm;
        // BigDecimal 타입을 Double로 변환하되, null 체크를 수행하여 안전성을 확보한다.
        this.grs = grs != null ? grs.doubleValue() : null;
        this.bsopPrfiInrt = bsopPrfiInrt != null ? bsopPrfiInrt.doubleValue() : null;
        this.rsrvRate = rsrvRate != null ? rsrvRate.doubleValue() : null;
        this.lbltRate = lbltRate != null ? lbltRate.doubleValue() : null;
        this.stckClpr = stckClpr;
        this.stckDryyHgpr = stckDryyHgpr != null ? stckDryyHgpr.doubleValue() : null;
        this.dryyHgprVrssPrprRate = dryyHgprVrssPrprRate != null ? dryyHgprVrssPrprRate.doubleValue() : null;
        this.ma5 = ma5 != null ? ma5.doubleValue() : null;
        this.ma10 = ma10 != null ? ma10.doubleValue() : null;
        this.ma20 = ma20 != null ? ma20.doubleValue() : null;
        this.ma30 = ma30 != null ? ma30.doubleValue() : null;
        this.ma60 = ma60 != null ? ma60.doubleValue() : null;
        this.ma120 = ma120 != null ? ma120.doubleValue() : null;
        this.ma240 = ma240 != null ? ma240.doubleValue() : null;
        this.frgnNtbyQty = frgnNtbyQty != null ? frgnNtbyQty.doubleValue() : null;
        this.pgtrNtbyQty = pgtrNtbyQty != null ? pgtrNtbyQty.doubleValue() : null;
        this.acmlVol = acmlVol;
        this.frgnHldnQty = frgnHldnQty != null ? frgnHldnQty.doubleValue() : null;
        this.lstnStcn = lstnStcn != null ? lstnStcn.doubleValue() : null;
        this.per = per != null ? per.doubleValue() : null;
        this.pbr = pbr != null ? pbr.doubleValue() : null;
        this.stckDryyLwpr = stckDryyLwpr != null ? stckDryyLwpr.doubleValue() : null;
        this.dryyLwprVrssPrprRate = dryyLwprVrssPrprRate != null ? dryyLwprVrssPrprRate.doubleValue() : null;
        this.eps = eps != null ? eps.doubleValue() : null;
        this.bps = bps != null ? bps.doubleValue() : null;
    }
}