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
import me.project.snowbot.entity.BalanceSheet;
import me.project.snowbot.entity.SheetPK;
import me.project.snowbot.repository.BalanceSheetRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 재무상태표(Balance Sheet) 데이터와 관련된 비즈니스 로직을 처리하는 서비스 클래스이다.
 * <p>
 * `SheetService` 인터페이스를 구현하며, `BalanceSheetRepository`를 사용하여
 * 데이터베이스에서 재무상태표 정보를 조회하거나 외부에서 입력받은 데이터를 저장 및 갱신(Upsert)하는 기능을 제공한다.
 * </p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BalanceSheetService implements SheetService {

    /** 재무상태표 엔티티에 접근하기 위한 리포지토리 */
    private final BalanceSheetRepository balanceSheetRepository;

    /**
     * 특정 종목 코드(id)에 해당하는 모든 재무상태표 내역을 조회한다.
     *
     * @param id 조회할 종목 코드 (Item Code)
     * @return 해당 종목의 과거 모든 시점의 재무상태표 엔티티 리스트
     */
    public List<BalanceSheet> findById(String id) {
        return balanceSheetRepository.findByIdAll(id);
    }

    /**
     * 외부(DTO)로부터 전달받은 재무상태표 데이터를 처리하여 데이터베이스에 저장하거나 기존 데이터를 갱신한다.
     * <p>
     * 이 메서드는 `@Transactional` 어노테이션을 통해 하나의 트랜잭션 범위 내에서 안전하게 실행된다.
     * `SheetData`에 포함된 다건의 데이터를 반복 처리하며, 각 데이터에 대해 다음 로직을 수행한다:
     * <ol>
     * <li><b>복합키 확인:</b> 입력받은 id(종목코드), cl(시트구분), 그리고 데이터 내의 stac_yymm(결산년월)을 조합하여 고유한 복합키를 구성한다.</li>
     * <li><b>Upsert 결정:</b> 해당 복합키로 기존 DB에 데이터가 있는지 조회한다.
     * <ul>
     * <li>데이터가 없으면: 새로운 `BalanceSheet` 및 `BalanceSheetPK` 객체를 생성하여 초기화한다.</li>
     * <li>데이터가 있으면: 기존 엔티티 객체를 가져와서 수정할 준비를 한다.</li>
     * </ul>
     * </li>
     * <li><b>데이터 매핑:</b> 입력 Map의 데이터를 엔티티의 필드(자산, 부채, 자본 항목들)에 매핑한다.
     * 이때 `CustomTypeConvert` 유틸리티를 사용하여 안전하게 `BigDecimal` 타입으로 변환한다.</li>
     * <li><b>저장:</b> 최종적으로 엔티티를 리포지토리를 통해 저장한다.</li>
     * </ol>
     * </p>
     *
     * @param id        종목 코드 (PK의 일부)
     * @param cl        시트 구분 코드 (PK의 일부, 예: 연결/별도 재무제표 구분)
     * @param sheetData 외부 API 등에서 수신한 원본 데이터가 담긴 DTO 객체. 내부에 실제 데이터 리스트(`output`)를 포함한다.
     */
    @Override
    @Transactional
    @SuppressWarnings("unchecked") // output 맵 캐스팅에 대한 경고 억제
    public void insert(String id, String cl, SheetData sheetData) {
        // DTO에서 실제 데이터 리스트를 안전하게 추출한다. null일 경우 빈 리스트를 반환한다.
        List<Object> innerList = Optional.ofNullable(sheetData.getOutput())
                .map(List::of)
                .orElse(Collections.emptyList());

        for (Object obj : innerList) {
            // 각 리스트 항목을 Map 형태로 캐스팅한다.
            Map<String, Object> output = (Map<String, Object>) obj;
            // 복합키의 마지막 구성 요소인 결산년월을 추출한다.
            String ym = String.valueOf(output.get("stac_yymm"));

            // [핵심 로직: Upsert 처리]
            // 복합키(id, cl, ym)로 기존 데이터를 조회하고, 없으면 새로 생성한다.
            BalanceSheet balanceSheet = Optional.ofNullable(balanceSheetRepository.findByKeys(id, cl, ym))
                    .orElseGet(() -> {
                        // 새 엔티티 생성 로직
                        SheetPK sheetPK = new SheetPK();
                        sheetPK.setItem_cd(id);
                        sheetPK.setSheet_cl(cl);
                        sheetPK.setStac_yymm(ym);

                        BalanceSheet newBalanceSheet = new BalanceSheet();
                        newBalanceSheet.setId(sheetPK);
                        return newBalanceSheet;
                    });

            // [데이터 매핑]
            // Map에서 값을 꺼내 BigDecimal로 변환 후 엔티티에 설정한다.
            balanceSheet.setCras(CustomTypeConvert.convBigDecimal(output.get("cras")));
            balanceSheet.setFxas(CustomTypeConvert.convBigDecimal(output.get("fxas")));
            balanceSheet.setTotal_aset(CustomTypeConvert.convBigDecimal(output.get("total_aset")));
            balanceSheet.setFlow_lblt(CustomTypeConvert.convBigDecimal(output.get("flow_lblt")));
            balanceSheet.setFix_lblt(CustomTypeConvert.convBigDecimal(output.get("fix_lblt")));
            balanceSheet.setTotal_lblt(CustomTypeConvert.convBigDecimal(output.get("total_lblt")));
            balanceSheet.setCpfn(CustomTypeConvert.convBigDecimal(output.get("cpfn")));
            balanceSheet.setCfp_surp(CustomTypeConvert.convBigDecimal(output.get("cfp_surp")));
            balanceSheet.setPrfi_surp(CustomTypeConvert.convBigDecimal(output.get("prfi_surp")));
            balanceSheet.setTotal_cptl(CustomTypeConvert.convBigDecimal(output.get("total_cptl")));

            // 엔티티 저장 (신규 생성 또는 기존 수정 반영)
            balanceSheetRepository.save(balanceSheet);
        }
    }
}