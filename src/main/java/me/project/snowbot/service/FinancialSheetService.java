package me.project.snowbot.service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.springframework.stereotype.Service;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.SheetData;
import me.project.snowbot.entity.FinancialSheet;
import me.project.snowbot.entity.SheetPK;
import me.project.snowbot.repository.FinancialSheetRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 재무제표(Financial Sheet) 관련 비즈니스 로직을 처리하는 서비스 클래스이다.
 * 재무 데이터 조회, ROE 평균 계산, 외부 API 데이터 적재 등의 기능을 수행한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class FinancialSheetService implements SheetService {

    private final FinancialSheetRepository financialSheetRepository;

    /**
     * 특정 종목(id)의 모든 재무제표 데이터를 조회한다.
     *
     * @param id 종목 코드
     * @return 해당 종목의 전체 재무제표 리스트
     */
    public List<FinancialSheet> findById(String id) {
        return financialSheetRepository.findByIdAll(id);
    }

    /**
     * 특정 종목(id)의 연간 재무제표 데이터를 조회한다.
     * (일반적으로 날짜 내림차순 등으로 정렬되어 있다고 가정한다.)
     *
     * @param id 종목 코드
     * @return 해당 종목의 연간 재무제표 리스트
     */
    public List<FinancialSheet> findByIdYear(String id) {
        return financialSheetRepository.findByIdYear(id);
    }

    /**
     * 최근 3년(혹은 최근 3개 데이터)의 평균 ROE(자기자본이익률)를 계산한다.
     *
     * @param id 종목 코드
     * @return 최근 3년 평균 ROE 값 (데이터가 없으면 0을 반환한다.)
     */
    public double roeAvg3(String id) {
        // 1. 해당 종목의 연간 재무 데이터를 조회한다.
        List<FinancialSheet> financialSheetList = findByIdYear(id);

        // 2. 최근 3개년 ROE 합계를 계산한다.
        double roeSum = financialSheetList.stream()
                .filter(sheet -> "0".equals(sheet.getId().getSheet_cl())) // 결산 구분: "0" (연간/확정 실적 등)만 필터링한다.
                .limit(3) // 최신 데이터 기준 최대 3개 항목만 처리한다.
                .mapToDouble(sheet -> {
                    try {
                        // BigDecimal 또는 String 형태의 ROE 값을 double로 변환한다.
                        return Double.parseDouble(sheet.getRoe_val().toString());
                    } catch (NumberFormatException e) {
                        log.warn("ROE parsing error for sheet id: {}", sheet.getId(), e);
                        return 0;
                    }
                })
                .sum();

        // 3. 실제 계산에 포함된 데이터 개수를 카운트한다. (0으로 나누기 방지)
        long roeCnt = financialSheetList.stream()
                .filter(sheet -> "0".equals(sheet.getId().getSheet_cl()))
                .limit(3)
                .count();

        // 4. 평균을 계산한다. (데이터가 하나라도 있으면 평균, 없으면 0이다.)
        return roeCnt > 0 ? roeSum / roeCnt : 0;
    }

    /**
     * 외부에서 수신한 재무제표 데이터를 DB에 저장하거나 업데이트한다.
     * (Upsert 로직: 기존 데이터가 있으면 업데이트하고, 없으면 신규 생성한다.)
     *
     * @param id        종목 코드
     * @param cl        재무제표 구분 (연간, 분기 등)
     * @param sheetData 외부 API 등에서 수신한 재무 데이터 DTO
     */
    @Override
    @Transactional
    public void insert(String id, String cl, SheetData sheetData) {
        // SheetData 내부의 output 리스트를 안전하게 추출한다. (null인 경우 빈 리스트를 반환한다.)
        List<Object> innerList = Optional.ofNullable(sheetData.getOutput())
                .map(List::of)
                .orElse(Collections.emptyList());

        for (Object obj : innerList) {
            Map<String, Object> output = (Map<String, Object>) obj;
            String ym = String.valueOf(output.get("stac_yymm")); // 결산 연월이다.

            // 1. 기존 데이터 존재 여부를 확인한다. (복합키: 종목코드, 구분, 연월)
            FinancialSheet financialSheet = Optional.ofNullable(financialSheetRepository.findByKeys(id, cl, ym))
                    .orElseGet(() -> {
                        // 2. 존재하지 않을 경우: 신규 엔티티 및 PK를 생성한다.
                        SheetPK sheetPK = new SheetPK();
                        sheetPK.setItem_cd(id);
                        sheetPK.setSheet_cl(cl);
                        sheetPK.setStac_yymm(ym);

                        FinancialSheet newFinancialSheet = new FinancialSheet();
                        newFinancialSheet.setId(sheetPK);
                        return newFinancialSheet;
                    });
            
            // 3. 데이터를 매핑한다. (매출액, 영업이익, 순이익, ROE, EPS, SPS, BPS, 유보율, 부채비율)
            // CustomTypeConvert를 사용하여 안전하게 타입 변환 후 설정한다.
            financialSheet.setGrs(CustomTypeConvert.convBigDecimal(output.get("grs")));
            financialSheet.setBsop_prfi_inrt(CustomTypeConvert.convBigDecimal(output.get("bsop_prfi_inrt")));
            financialSheet.setNtin_inrt(CustomTypeConvert.convBigDecimal(output.get("ntin_inrt")));
            financialSheet.setRoe_val(CustomTypeConvert.convBigDecimal(output.get("roe_val")));
            financialSheet.setEps(CustomTypeConvert.convBigDecimal(output.get("eps")));
            financialSheet.setSps(CustomTypeConvert.convBigDecimal(output.get("sps")));
            financialSheet.setBps(CustomTypeConvert.convBigDecimal(output.get("bps")));
            financialSheet.setRsrv_rate(CustomTypeConvert.convBigDecimal(output.get("rsrv_rate")));
            financialSheet.setLblt_rate(CustomTypeConvert.convBigDecimal(output.get("lblt_rate")));

            // 4. 저장한다. (JPA는 식별자가 있으면 merge, 없으면 persist를 수행한다.)
            financialSheetRepository.save(financialSheet);
        }
    }
}