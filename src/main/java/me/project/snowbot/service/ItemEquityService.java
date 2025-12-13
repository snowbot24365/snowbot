package me.project.snowbot.service;

import java.util.Map;
import java.util.Optional;

import org.springframework.stereotype.Service;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.Body;
import me.project.snowbot.entity.ItemEquity;
import me.project.snowbot.repository.ItemEquityRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 주식 종목(Equity Item) 정보와 관련된 비즈니스 로직을 처리하는 서비스 클래스이다.
 * <p>
 * `ItemEquityRepository`를 사용하여 데이터베이스 접근을 수행하며,
 * 종목 정보의 조회 및 생성/수정(Upsert) 기능을 제공한다.
 * </p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ItemEquityService {

    /** 주식 종목 엔티티에 접근하기 위한 리포지토리이다. */
    private final ItemEquityRepository itemEquityRepository;

    /**
     * 주어진 종목 코드(id)에 해당하는 주식 종목 정보를 조회한다.
     *
     * @param id 조회할 종목의 코드(itemCd)이다.
     * @return 조회된 `ItemEquity` 엔티티 객체이다. 존재하지 않을 경우 `null`이 반환될 수 있다.
     */
    public ItemEquity findById(String id) {
        return itemEquityRepository.findByKey(id);
    }

    /**
     * 외부 API로부터 받아온 종목 정보를 데이터베이스에 저장하거나 업데이트한다.
     * <p>
     * 1. 주어진 종목 코드(id)로 기존 데이터를 조회한다.
     * 2. 데이터가 없으면 새로운 `ItemEquity` 객체를 생성한다.
     * 3. `Body` 객체에 담긴 상세 정보를 `ItemEquity` 엔티티의 필드에 매핑한다.
     * 이 과정에서 `CustomTypeConvert`를 사용하여 데이터 타입 변환을 수행한다.
     * 4. 매핑된 엔티티를 데이터베이스에 저장(save)한다. (기존 데이터가 있으면 수정, 없으면 생성된다.)
     * </p>
     * 이 메서드는 트랜잭션 안에서 실행된다.
     *
     * @param id   저장할 종목의 코드(itemCd)이다.
     * @param body 외부 API로부터 받은 응답 데이터(`Body`) 객체이다. 내부에 종목 상세 정보(`output` 맵)를 포함하고 있다.
     */
    @Transactional
    @SuppressWarnings("unchecked") // body.getOutput()의 캐스팅 경고를 억제한다.
    public void insert(String id, Body body) {
        // Body 객체에서 상세 정보가 담긴 Map을 추출한다.
        Map<String, Object> output = (Map<String, Object>) body.getOutput();

        // 기존 종목 정보를 조회하고, 없으면 새로 생성한다 (Upsert 준비).
        ItemEquity itemEquity = Optional.ofNullable(itemEquityRepository.findByKey(id))
                .orElseGet(() -> {
                    ItemEquity newItemEquity = new ItemEquity();
                    newItemEquity.setItemCd(id); // 새 객체 생성 시 식별자(ID) 설정
                    return newItemEquity;
                });

        // --- Map의 데이터를 엔티티 필드에 매핑 시작 ---
        // 문자열 데이터 매핑
        itemEquity.setBstp_kor_isnm(String.valueOf(output.get("bstp_kor_isnm")));
        itemEquity.setIscd_stat_cls_code(String.valueOf(output.get("iscd_stat_cls_code")));

        // 숫자(BigDecimal) 데이터 매핑 (CustomTypeConvert 유틸리티 사용)
        itemEquity.setStck_sdpr(CustomTypeConvert.convBigDecimal(output.get("stck_sdpr")));
        itemEquity.setWghn_avrg_stck_prc(CustomTypeConvert.convBigDecimal(output.get("wghn_avrg_stck_prc")));
        itemEquity.setHts_frgn_ehrt(CustomTypeConvert.convBigDecimal(output.get("hts_frgn_ehrt")));
        itemEquity.setFrgn_ntby_qty(CustomTypeConvert.convBigDecimal(output.get("frgn_ntby_qty")));
        itemEquity.setPgtr_ntby_qty(CustomTypeConvert.convBigDecimal(output.get("pgtr_ntby_qty")));
        itemEquity.setCpfn(CustomTypeConvert.convBigDecimal(output.get("cpfn")));
        itemEquity.setRstc_wdth_prc(CustomTypeConvert.convBigDecimal(output.get("rstc_wdth_prc")));
        itemEquity.setStck_fcam(CustomTypeConvert.convBigDecimal(output.get("stck_fcam")));
        itemEquity.setStck_sspr(CustomTypeConvert.convBigDecimal(output.get("stck_sspr")));
        itemEquity.setAspr_unit(CustomTypeConvert.convBigDecimal(output.get("aspr_unit")));
        itemEquity.setHts_deal_qty_unit_val(CustomTypeConvert.convBigDecimal(output.get("hts_deal_qty_unit_val")));
        itemEquity.setLstn_stcn(CustomTypeConvert.convBigDecimal(output.get("lstn_stcn")));
        itemEquity.setHts_avls(CustomTypeConvert.convBigDecimal(output.get("hts_avls")));
        itemEquity.setVol_tnrt(CustomTypeConvert.convBigDecimal(output.get("vol_tnrt")));

        // 250일 최고/최저 관련 데이터 매핑
        itemEquity.setD250_hgpr(CustomTypeConvert.convBigDecimal(output.get("d250_hgpr")));
        itemEquity.setD250_hgpr_date(String.valueOf(output.get("d250_hgpr_date")));
        itemEquity.setD250_hgpr_vrss_prpr_rate(CustomTypeConvert.convBigDecimal(output.get("d250_hgpr_vrss_prpr_rate")));
        itemEquity.setD250_lwpr(CustomTypeConvert.convBigDecimal(output.get("d250_lwpr")));
        itemEquity.setD250_lwpr_date(String.valueOf(output.get("d250_lwpr_date")));
        itemEquity.setD250_lwpr_vrss_prpr_rate(CustomTypeConvert.convBigDecimal(output.get("d250_lwpr_vrss_prpr_rate")));

        // 연중 최고/최저 관련 데이터 매핑
        itemEquity.setStck_dryy_hgpr(CustomTypeConvert.convBigDecimal(output.get("stck_dryy_hgpr")));
        itemEquity.setDryy_hgpr_date(String.valueOf(output.get("dryy_hgpr_date")));
        itemEquity.setDryy_hgpr_vrss_prpr_rate(CustomTypeConvert.convBigDecimal(output.get("dryy_hgpr_vrss_prpr_rate")));
        itemEquity.setStck_dryy_lwpr(CustomTypeConvert.convBigDecimal(output.get("stck_dryy_lwpr")));
        itemEquity.setDryy_lwpr_date(String.valueOf(output.get("dryy_lwpr_date")));
        itemEquity.setDryy_lwpr_vrss_prpr_rate(CustomTypeConvert.convBigDecimal(output.get("dryy_lwpr_vrss_prpr_rate")));

        // 52주 최고/최저 관련 데이터 매핑
        itemEquity.setW52_hgpr(CustomTypeConvert.convBigDecimal(output.get("w52_hgpr")));
        itemEquity.setW52_hgpr_date(String.valueOf(output.get("w52_hgpr_date")));
        itemEquity.setW52_hgpr_vrss_prpr_ctrt(CustomTypeConvert.convBigDecimal(output.get("w52_hgpr_vrss_prpr_ctrt")));
        itemEquity.setW52_lwpr(CustomTypeConvert.convBigDecimal(output.get("w52_lwpr")));
        itemEquity.setW52_lwpr_date(String.valueOf(output.get("w52_lwpr_date")));
        itemEquity.setW52_lwpr_vrss_prpr_ctrt(CustomTypeConvert.convBigDecimal(output.get("w52_lwpr_vrss_prpr_ctrt")));

        // 기타 재무 및 상태 정보 매핑
        itemEquity.setWhol_loan_rmnd_rate(CustomTypeConvert.convBigDecimal(output.get("whol_loan_rmnd_rate")));
        itemEquity.setSsts_yn(String.valueOf(output.get("ssts_yn")));
        itemEquity.setFcam_cnnm(String.valueOf(output.get("fcam_cnnm")));
        itemEquity.setCpfn_cnnm(String.valueOf(output.get("cpfn_cnnm")));
        itemEquity.setLast_ssts_cntg_qty(CustomTypeConvert.convBigDecimal(output.get("last_ssts_cntg_qty")));
        itemEquity.setFrgn_hldn_qty(CustomTypeConvert.convBigDecimal(output.get("frgn_hldn_qty")));

        // 투자 지표(PER, EPS 등) 매핑
        itemEquity.setPer(CustomTypeConvert.convBigDecimal(output.get("per")));
        itemEquity.setEps(CustomTypeConvert.convBigDecimal(output.get("eps")));
        itemEquity.setPbr(CustomTypeConvert.convBigDecimal(output.get("pbr")));
        itemEquity.setBps(CustomTypeConvert.convBigDecimal(output.get("bps")));

        // 상한가/하한가 매핑
        itemEquity.setStck_mxpr(CustomTypeConvert.convBigDecimal(output.get("stck_mxpr")));
        itemEquity.setStck_llam(CustomTypeConvert.convBigDecimal(output.get("stck_llam")));
        // --- Map의 데이터를 엔티티 필드에 매핑 종료 ---

        // 최종적으로 엔티티를 저장한다.
        itemEquityRepository.save(itemEquity);
    }
}