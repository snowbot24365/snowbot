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
import me.project.snowbot.entity.ProfitSheet;
import me.project.snowbot.entity.SheetPK;
import me.project.snowbot.repository.ProfitSheetRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 기업의 수익성 지표(Profit Sheet) 관련 비즈니스 로직을 처리하는 서비스 클래스이다.
 * 매출액 이익률, 자본 이익률 등 수익성 관련 데이터의 조회 및 저장을 담당한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ProfitSheetService implements SheetService {

    private final ProfitSheetRepository profitSheetRepository;

    /**
     * 특정 종목(id)의 모든 수익성 지표 데이터를 조회한다.
     *
     * @param id 종목 코드
     * @return 해당 종목의 전체 수익성 지표 리스트
     */
    public List<ProfitSheet> findById(String id) {
        return profitSheetRepository.findByIdAll(id);
    }

    /**
     * 외부에서 수신한 수익성 지표 데이터를 DB에 저장하거나 업데이트한다.
     * (Upsert 로직: 기존 데이터가 있으면 업데이트하고, 없으면 신규 생성한다.)
     *
     * @param id        종목 코드
     * @param cl        재무제표 구분 (연간, 분기 등)
     * @param sheetData 외부 API 등에서 수신한 수익성 데이터 DTO
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
            ProfitSheet profitSheet = Optional.ofNullable(profitSheetRepository.findByKeys(id, cl, ym))
                    .orElseGet(() -> {
                        // 2. 존재하지 않을 경우: 신규 엔티티 및 PK를 생성한다.
                        SheetPK sheetPK = new SheetPK();
                        sheetPK.setItem_cd(id);
                        sheetPK.setSheet_cl(cl);
                        sheetPK.setStac_yymm(ym);

                        ProfitSheet newProfitSheet = new ProfitSheet();
                        newProfitSheet.setId(sheetPK);
                        return newProfitSheet;
                    });

            // 3. 데이터를 매핑한다.
            // CustomTypeConvert를 사용하여 안전하게 타입 변환 후 설정한다.
            // (총자본순이익률, 자기자본순이익률, 매출액순이익률, 매출액총이익률 등)
            profitSheet.setCptl_ntin_rate(CustomTypeConvert.convBigDecimal(output.get("cptl_ntin_rate")));
            profitSheet.setSelf_cptl_ntin_inrt(CustomTypeConvert.convBigDecimal(output.get("self_cptl_ntin_inrt")));
            profitSheet.setSale_ntin_rate(CustomTypeConvert.convBigDecimal(output.get("sale_ntin_rate")));
            profitSheet.setSale_totl_rate(CustomTypeConvert.convBigDecimal(output.get("sale_totl_rate")));

            // 4. 저장한다. (JPA는 식별자가 있으면 merge, 없으면 persist를 수행한다.)
            profitSheetRepository.save(profitSheet);
        }
    }
}