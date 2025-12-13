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
import me.project.snowbot.entity.EtcSheet;
import me.project.snowbot.entity.SheetPK;
import me.project.snowbot.repository.EtcSheetRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 기타 재무 지표(Etc Sheet) 관련 비즈니스 로직을 처리하는 서비스 클래스이다.
 * EBITDA, EV/EBITDA 등 기업 가치 평가에 필요한 보조 지표의 조회 및 저장을 담당한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EtcSheetService implements SheetService {

    private final EtcSheetRepository etcSheetRepository;

    /**
     * 특정 종목(id)의 모든 기타 재무 지표 데이터를 조회한다.
     *
     * @param id 종목 코드
     * @return 해당 종목의 전체 기타 지표 리스트
     */
    public List<EtcSheet> findById(String id) {
        return etcSheetRepository.findByIdAll(id);
    }

    /**
     * 외부에서 수신한 기타 재무 지표 데이터를 DB에 저장하거나 업데이트한다.
     * (Upsert 로직: 기존 데이터가 있으면 업데이트하고, 없으면 신규 생성한다.)
     *
     * @param id        종목 코드
     * @param cl        재무제표 구분 (연간, 분기 등)
     * @param sheetData 외부 API 등에서 수신한 기타 지표 데이터 DTO
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
            EtcSheet etcSheet = Optional.ofNullable(etcSheetRepository.findByKeys(id, cl, ym))
                    .orElseGet(() -> {
                        // 2. 존재하지 않을 경우: 신규 엔티티 및 PK를 생성한다.
                        SheetPK sheetPK = new SheetPK();
                        sheetPK.setItem_cd(id);
                        sheetPK.setSheet_cl(cl);
                        sheetPK.setStac_yymm(ym);

                        EtcSheet newEtcSheet = new EtcSheet();
                        newEtcSheet.setId(sheetPK);
                        return newEtcSheet;
                    });

            // 3. 데이터를 매핑한다.
            // CustomTypeConvert를 사용하여 안전하게 타입 변환 후 설정한다.
            // (EBITDA: 상각전영업이익, EV/EBITDA: 기업가치 대비 상각전영업이익 비율)
            etcSheet.setEbitda(CustomTypeConvert.convBigDecimal(output.get("ebitda")));
            etcSheet.setEv_ebitda(CustomTypeConvert.convBigDecimal(output.get("ev_ebitda")));

            // 4. 저장한다. (JPA는 식별자가 있으면 merge, 없으면 persist를 수행한다.)
            etcSheetRepository.save(etcSheet);
        }
    }
}