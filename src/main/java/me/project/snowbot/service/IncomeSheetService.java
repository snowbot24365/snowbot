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
import me.project.snowbot.entity.IncomeSheet;
import me.project.snowbot.entity.SheetPK;
import me.project.snowbot.repository.IncomeSheetRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 손익계산서(Income Sheet) 데이터 관련 비즈니스 로직을 수행하는 서비스 클래스이다.
 * <p>
 * `SheetService` 인터페이스를 구현하며, `IncomeSheetRepository`를 사용하여 데이터베이스 접근을 담당한다.
 * 주요 기능으로 특정 종목의 손익계산서 내역 조회 및 외부 데이터 기반의 저장/갱신(Upsert) 로직을 제공한다.
 * </p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class IncomeSheetService implements SheetService {

    /** 손익계산서 엔티티의 데이터베이스 조작을 담당하는 리포지토리이다. */
    private final IncomeSheetRepository incomeSheetRepository;

    /**
     * 주어진 종목 코드(ID)에 해당하는 모든 손익계산서 내역을 조회한다.
     *
     * @param id 조회할 종목 코드 (Item Code)
     * @return 해당 종목의 과거 시점별 손익계산서 엔티티 리스트
     */
    public List<IncomeSheet> findByid(String id) {
        return incomeSheetRepository.findByIdAll(id);
    }

    /**
     * 외부 DTO로부터 전달받은 손익계산서 데이터를 데이터베이스에 저장하거나, 이미 존재할 경우 갱신한다 (Upsert).
     * <p>
     * 이 메서드는 트랜잭션 범위 내에서 실행된다. `SheetData` DTO 내의 데이터 리스트를 순회하며
     * 각 항목에 대해 다음과 같은 절차를 수행한다:
     * <ol>
     * <li>입력받은 파라미터(id, cl)와 데이터 내의 결산년월(stac_yymm)을 조합하여 고유한 복합키(PK)를 구성한다.</li>
     * <li>해당 복합키로 데이터베이스에 기존 데이터가 존재하는지 조회한다.</li>
     * <li>데이터가 존재하면 기존 엔티티를 가져와 업데이트를 준비하고, 존재하지 않으면 새로운 엔티티와 PK 객체를 생성한다.</li>
     * <li>원본 Map 데이터의 값을 `CustomTypeConvert` 유틸리티를 사용하여 안전하게 변환한 후 엔티티의 필드에 매핑한다.</li>
     * <li>최종적으로 리포지토리를 통해 데이터를 저장(save)한다.</li>
     * </ol>
     * </p>
     *
     * @param id        종목 코드 (Composite Key의 일부)
     * @param cl        재무제표 구분 코드 (Composite Key의 일부; 예: 연간, 분기 등)
     * @param sheetData 외부 API 등에서 수신한 원본 데이터 DTO 객체. 내부에 실제 데이터 맵 리스트(`output`)를 포함한다.
     */
    @Override
    @Transactional
    @SuppressWarnings("unchecked") // output 데이터를 Map<String, Object>로 캐스팅할 때 발생하는 경고 억제
    public void insert(String id, String cl, SheetData sheetData) {
        // DTO에서 실제 데이터 리스트를 추출한다. null일 경우 빈 리스트를 반환하여 안전하게 처리한다.
        List<Object> innerList = Optional.ofNullable(sheetData.getOutput())
                .map(List::of)
                .orElse(Collections.emptyList());

        for (Object obj : innerList) {
            // 데이터 항목을 Map 형태로 캐스팅한다.
            Map<String, Object> output = (Map<String, Object>) obj;
            // 복합키의 구성 요소인 결산년월을 추출한다.
            String ym = String.valueOf(output.get("stac_yymm"));

            // [핵심 로직: Upsert 처리]
            // 복합키(id, cl, ym)를 기준으로 기존 데이터를 조회하고, 없으면(orElseGet) 새로 생성한다.
            IncomeSheet incomeSheet = Optional.ofNullable(incomeSheetRepository.findByKeys(id, cl, ym))
                    .orElseGet(() -> {
                        // 새 엔티티 생성 시 PK 객체도 함께 초기화한다.
                        SheetPK sheetPK = new SheetPK();
                        sheetPK.setItem_cd(id);
                        sheetPK.setSheet_cl(cl);
                        sheetPK.setStac_yymm(ym);

                        IncomeSheet newIncomeSheet = new IncomeSheet();
                        newIncomeSheet.setId(sheetPK);
                        return newIncomeSheet;
                    });

            // [데이터 매핑]
            // Map에서 값을 추출하여 BigDecimal로 변환 후 엔티티 필드에 설정한다.
            incomeSheet.setSale_account(CustomTypeConvert.convBigDecimal(output.get("sale_account"))); // 매출액
            incomeSheet.setSale_cost(CustomTypeConvert.convBigDecimal(output.get("sale_cost")));       // 매출원가
            incomeSheet.setSale_totl_prfi(CustomTypeConvert.convBigDecimal(output.get("sale_totl_prfi"))); // 매출총이익
            incomeSheet.setDepr_cost(CustomTypeConvert.convBigDecimal(output.get("depr_cost")));       // 감가상각비
            incomeSheet.setSell_mang(CustomTypeConvert.convBigDecimal(output.get("sell_mang")));       // 판매비와관리비
            incomeSheet.setBsop_prti(CustomTypeConvert.convBigDecimal(output.get("bsop_prti")));       // 영업이익
            incomeSheet.setBsop_non_ernn(CustomTypeConvert.convBigDecimal(output.get("bsop_non_ernn"))); // 영업외수익
            incomeSheet.setBsop_non_expn(CustomTypeConvert.convBigDecimal(output.get("bsop_non_expn"))); // 영업외비용
            incomeSheet.setOp_prfi(CustomTypeConvert.convBigDecimal(output.get("op_prfi")));           // 경상이익(법인세비용차감전순이익)
            incomeSheet.setSpec_prfi(CustomTypeConvert.convBigDecimal(output.get("spec_prfi")));       // 특별이익
            incomeSheet.setSpec_loss(CustomTypeConvert.convBigDecimal(output.get("spec_loss")));       // 특별손실
            incomeSheet.setThtr_ntin(CustomTypeConvert.convBigDecimal(output.get("thtr_ntin")));       // 당기순이익

            // 엔티티 저장 (신규 생성 또는 기존 수정 반영)
            incomeSheetRepository.save(incomeSheet);
        }
    }
}