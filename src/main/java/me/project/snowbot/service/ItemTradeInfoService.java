package me.project.snowbot.service;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Service;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.ItemPrice;
import me.project.snowbot.entity.ItemTradeInfo;
import me.project.snowbot.entity.ItemTradeInfoPK;
import me.project.snowbot.entity.SwingScorePK;
import me.project.snowbot.repository.ItemTradeInfoRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 종목별 매매 전략 정보(ItemTradeInfo)를 관리하는 서비스 클래스이다.
 * 전일 시세 데이터를 기반으로 피벗(Pivot) 지지/저항선을 계산하고, 매수 가능성 여부를 업데이트하는 로직을 수행한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ItemTradeInfoService {
    private final ItemTradeInfoRepository itemTradeInfoRepository;
    private final ItemPriceService itemPriceService;

    /**
     * 특정 종목(id)과 날짜(date)에 해당하는 매매 정보를 단건 조회한다.
     */
    public ItemTradeInfo getItemTradeInfo(String id, String date) {
        return itemTradeInfoRepository.findByKey(id, date);
    }

    /**
     * 특정 날짜에 'SW'(스윙 전략 등) 타입으로 분류되고 매수 가능성이 있는 종목 리스트를 조회한다.
     */
    public List<ItemTradeInfo> getBuySWItems(String date) {
        return itemTradeInfoRepository.findByDateAndTypeAndYn_possibility(date, "SW");
    }

    /**
     * 날짜와 분석 유형(type)을 기준으로 매매 정보 리스트를 조회한다.
     */
    public List<ItemTradeInfo> findByDateAndType(String date, String type) {
        return itemTradeInfoRepository.findByDateAndType(date, type);
    }

    /**
     * 특정 날짜에 매수 가능성(Y)이 있는 모든 종목을 조회한다.
     */
    public List<ItemTradeInfo> getItemTradeInfos(String date) {
        return itemTradeInfoRepository.findByPossibleOpt(date);
    }

    /**
     * 전일 시세 데이터와 금일 시가/고가/저가 정보를 바탕으로 피벗(Pivot) 및 지지/저항선(R1~R3, S1~S3)을 계산하여 저장한다.
     * 
     *
     * @param id 종목 코드
     * @param date 기준 날짜
     * @param stckOprc 금일 시가
     * @param stckHgpr 금일 고가
     * @param stckLwpr 금일 저가
     * @param type 분석 전략 타입
     */
    @Transactional
    public void updateTradeInfoPoint(String id, String date, int stckOprc, int stckHgpr, int stckLwpr, String type) {

        // 1. 전일 가격 정보를 조회한다. (데이터가 존재할 경우에만 로직을 수행한다.)
        Optional<ItemPrice> itemPriceOpt = Optional.ofNullable(itemPriceService.findFirstByid(id));
        itemPriceOpt.ifPresent(itemPrice -> {
            int prdyOprc = CustomTypeConvert.convInteger(itemPrice.getStck_oprc()); // 전일 시가
            int prdyHgpr = CustomTypeConvert.convInteger(itemPrice.getStck_hgpr()); // 전일 고가
            int prdyLwpr = CustomTypeConvert.convInteger(itemPrice.getStck_lwpr()); // 전일 저가
            int prdyClpr = CustomTypeConvert.convInteger(itemPrice.getStck_clpr()); // 전일 종가

            // 2. 피벗(Pivot) 포인트 및 1차 지지/저항선을 계산한다.
            // Pivot = (전일 고가 + 전일 저가 + 전일 종가) / 3
            int pivotPoint = (prdyHgpr + prdyLwpr + prdyClpr) / 3;
            // R1 (1차 저항) = Pivot * 2 - 전일 저가
            int r1 = (pivotPoint * 2) - prdyLwpr;
            // S1 (1차 지지) = Pivot * 2 - 전일 고가
            int s1 = (pivotPoint * 2) - prdyHgpr;

            // 3. 변동폭(Range)을 계산하고 2차, 3차 지지/저항선을 계산한다.
            // (금일 시가가 0보다 클 때만, 즉 장이 시작된 이후에만 계산한다.)
            int priceDiff = stckHgpr - stckLwpr; // 고가 - 저가
            int r2 = stckOprc > 0 ? pivotPoint + priceDiff : 0;
            int r3 = stckOprc > 0 ? r1 + priceDiff : 0;
            int s2 = stckOprc > 0 ? pivotPoint - priceDiff : 0;
            int s3 = stckOprc > 0 ? s1 - priceDiff : 0;

            // 4. 기존 매매 정보가 있으면 가져오고, 없으면 새로 생성한다 (Upsert).
            ItemTradeInfo itemTradeInfo = Optional.ofNullable(itemTradeInfoRepository.findByKey(id, date))
                    .orElseGet(() -> {
                        ItemTradeInfoPK itemTradeInfoPK = new ItemTradeInfoPK();
                        itemTradeInfoPK.setItem_cd(id);
                        itemTradeInfoPK.setStckBsopDate(date);
                        ItemTradeInfo newItemTradeInfo = new ItemTradeInfo();
                        newItemTradeInfo.setId(itemTradeInfoPK);
                        newItemTradeInfo.setYn_possibility(""); // 초기값 설정
                        return newItemTradeInfo;
                    });

            // 5. 계산된 지표들을 엔티티에 설정한다.
            itemTradeInfo.setPivot(pivotPoint);
            itemTradeInfo.setR1(r1);
            itemTradeInfo.setS1(s1);
            itemTradeInfo.setStck_prdy_clpr(prdyClpr);
            if (stckOprc > 0) {
                itemTradeInfo.setR2(r2);
                itemTradeInfo.setR3(r3);
                itemTradeInfo.setS2(s2);
                itemTradeInfo.setS3(s3);
                itemTradeInfo.setStck_oprc(stckOprc);
            }
            itemTradeInfo.setCd_type(type);

            // 6. DB에 저장한다.
            itemTradeInfoRepository.save(itemTradeInfo);
        });
    }

    /**
     * 특정 종목의 매수 가능성 여부(yn), 비고(rmk), 전략 타입(type)을 업데이트한다.
     * 데이터가 존재하지 않을 경우 새로 생성하여 저장한다.
     */
    @Transactional
    public void updatePossibility(String id, String date, String yn, String rmk, String type) {
        ItemTradeInfo itemTradeInfo = Optional.ofNullable(itemTradeInfoRepository.findByKey(id, date))
                .orElseGet(() -> {
                    ItemTradeInfoPK itemTradeInfoPK = new ItemTradeInfoPK();
                    itemTradeInfoPK.setItem_cd(id);
                    itemTradeInfoPK.setStckBsopDate(date);
                    ItemTradeInfo newItemTradeInfo = new ItemTradeInfo();
                    newItemTradeInfo.setId(itemTradeInfoPK);
                    return newItemTradeInfo;
                });

        itemTradeInfo.setYn_possibility(yn);
        itemTradeInfo.setRmk(rmk);
        itemTradeInfo.setCd_type(type);
        itemTradeInfoRepository.save(itemTradeInfo);
    }

    /**
     * 이미 존재하는 매매 정보의 현재가(prpr)와 시가(oprc)를 실시간으로 업데이트한다.
     * 데이터가 존재할 경우에만 수행한다.
     */
    @Transactional
    public void updateTradeInfoPrpr(String id, String date, int prpr, int oprc) {
        Optional<ItemTradeInfo> itemTradeInfoOpt = Optional.ofNullable(itemTradeInfoRepository.findByKey(id, date));
        itemTradeInfoOpt.ifPresent(itemTradeInfo -> {
            itemTradeInfo.setStck_prpr(prpr);
            itemTradeInfo.setStck_oprc(oprc);
            itemTradeInfoRepository.save(itemTradeInfo);
        });
    }

    /**
     * 특정 종목 및 날짜에 대한 매수 가능성(yn) 및 비고(rmk) 정보를 저장하거나 업데이트하는 메서드이다 (Upsert).
     *
     * @param id 종목 코드
     * @param date 기준 날짜
     * @param yn 매수 가능성 여부 (Y/N 등)
     * @param cdType 분석 유형 코드
     * @param rmk 비고 사항
     */
    @Transactional
    public void saveItemTradeInfoByLast(String id, String date, String yn, String cdType, String rmk) {
        // 1. 주어진 키(종목 코드, 날짜)로 기존 데이터를 조회한다.
        ItemTradeInfo itemTradeInfo = itemTradeInfoRepository.findByKey(id, date);

        // 2. 데이터가 존재하지 않을 경우 (null) 새로운 엔티티 객체를 생성한다.
        if (itemTradeInfo == null) {
           ItemTradeInfoPK itemTradeInfoPK = new ItemTradeInfoPK();
            itemTradeInfoPK.setItem_cd(id);
            itemTradeInfoPK.setStckBsopDate(date);
            itemTradeInfo = new ItemTradeInfo();
            itemTradeInfo.setId(itemTradeInfoPK);
            // 새로 생성할 경우, 분석 유형 코드를 설정한다.
            itemTradeInfo.setCd_type(cdType);
        }

        // 3. 매수 가능성 여부와 비고 사항을 설정한다 (기존 데이터인 경우 업데이트된다).
        itemTradeInfo.setYn_possibility(yn);
        itemTradeInfo.setRmk(rmk);

        // 4. 트랜잭션을 통해 최종적으로 엔티티를 저장하거나 수정한다.
        itemTradeInfoRepository.save(itemTradeInfo);
    }
}