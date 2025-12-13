package me.project.snowbot.service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.IndexData;
import me.project.snowbot.entity.ItemPrice;
import me.project.snowbot.entity.ItemPricePK;
import me.project.snowbot.repository.ItemPriceRepository;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 종목별 시세 데이터(ItemPrice)의 조회, 저장, 삭제 및 보조지표(이동평균선) 계산을 담당하는 서비스 클래스이다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ItemPriceService {
    private final ItemPriceRepository itemPriceRepository;

    /**
     * 특정 종목 코드(id)에 해당하는 모든 시세 데이터를 조회한다.
     * @param id 종목 코드
     * @return 시세 데이터 리스트
     */
    public List<ItemPrice> findById(String id) {
        return itemPriceRepository.findByIdAll(id);
    }

    /**
     * 특정 종목 코드(id)에 해당하는 가장 최신(또는 첫 번째) 시세 데이터를 조회한다.
     */
    public ItemPrice findFirstByid(String id) {
        return itemPriceRepository.findFirstById(id);
    }

    /**
     * 종목 코드와 날짜를 기준으로 가장 먼저 검색되는 시세 데이터를 조회한다.
     */
    public ItemPrice findFirstByIdAndDate(String id, String date) {
        return itemPriceRepository.findFirstByIdAndDate(id, date);
    }

    /**
     * 종목 코드와 날짜를 복합키로 사용하여 특정 시세 데이터를 단건 조회한다.
     */
    public ItemPrice findByIdDate(String id, String date) {
        return itemPriceRepository.findByIdData(id, date);
    }

    /**
     * 특정 날짜에 해당하는 모든 종목의 시세 데이터를 조회한다.
     */
    public List<ItemPrice> findByDate(String date) {
        return itemPriceRepository.findByDate(date);
    }

    /**
     * 종목 코드와 조회 시작일, 종료일을 기준으로 기간 내의 시세 데이터를 조회한다.
     */
    public List<ItemPrice> findByIdAndRangeDate(String id, String fromDate, String toDate) {
        return itemPriceRepository.findByIdAndRangeDate(id, fromDate, toDate);
    }

    /**
     * 외부 API 등에서 수신한 인덱스 데이터(IndexData)를 파싱하여 DB에 저장하거나 업데이트한다.
     * 트랜잭션 내에서 처리하며, 기존 데이터가 존재하면 업데이트하고 없으면 새로 생성한다.
     *
     * @param id 종목 코드
     * @param indexData 수신된 시세 데이터 객체
     */
    @Transactional
    public void insert(String id, IndexData indexData) {
        // 1. 수신된 데이터에서 실제 시세 리스트(output2)를 추출한다. null일 경우 빈 리스트를 반환한다.
        List<Object> innerList = Optional.ofNullable(indexData.getOutput2())
                .map(List::of)
                .orElse(Collections.emptyList());

        for (Object obj : innerList) {
            Map<String, Object> output2 = (Map<String, Object>) obj;
            // 2. 유효한 데이터가 있는지 확인한다.
            if (output2 != null && output2.size() > 0) {
                String date = String.valueOf(output2.get("stck_bsop_date"));

                // 3. DB에서 해당 종목/날짜의 데이터를 조회한다. 없으면 새로운 엔티티 객체를 생성한다(Upsert 로직).
                ItemPrice itemPrice = Optional.ofNullable(itemPriceRepository.findByIdData(id, date))
                        .orElseGet(() -> {
                            ItemPricePK itemPricePK = new ItemPricePK();
                            itemPricePK.setItem_cd(id);
                            itemPricePK.setStck_bsop_date(date);
                            ItemPrice newItemPrice = new ItemPrice();
                            newItemPrice.setId(itemPricePK);
                            return newItemPrice;
                        });

                // 4. 수신된 맵(Map) 데이터에서 값을 추출하여 엔티티에 설정한다. 형변환 유틸리티를 사용한다.
                itemPrice.setStck_clpr(CustomTypeConvert.convInteger(output2.get("stck_clpr")));       // 종가
                itemPrice.setStck_oprc(CustomTypeConvert.convInteger(output2.get("stck_oprc")));       // 시가
                itemPrice.setStck_hgpr(CustomTypeConvert.convInteger(output2.get("stck_hgpr")));       // 고가
                itemPrice.setStck_lwpr(CustomTypeConvert.convInteger(output2.get("stck_lwpr")));       // 저가
                itemPrice.setAcml_vol(CustomTypeConvert.convInteger(output2.get("acml_vol")));         // 누적 거래량
                itemPrice.setAcml_tr_pbmn(CustomTypeConvert.convBigDecimal(output2.get("acml_tr_pbmn"))); // 누적 거래 대금
                itemPrice.setPrdy_vrss(CustomTypeConvert.convInteger(output2.get("prdy_vrss")));       // 전일 대비
                itemPrice.setPrdy_vrss_sign(CustomTypeConvert.convInteger(output2.get("prdy_vrss_sign"))); // 전일 대비 부호

                // 5. 엔티티를 저장한다.
                itemPriceRepository.save(itemPrice);
            }
        }
    }

    /**
     * 특정 날짜의 데이터를 조회하여 일괄 삭제한다.
     * @param date 삭제할 기준 날짜
     */
    @Transactional
    public void delete(String date) {
        List<ItemPrice> itemPriceList = itemPriceRepository.findByDataDel(date);
        for (ItemPrice itemPrice : itemPriceList) {
            itemPriceRepository.delete(itemPrice);
        }
    }

    /**
     * 주어진 시세 리스트를 기반으로 이동평균선(MA) 값을 계산하여 업데이트한다.
     * 5, 10, 20, 30, 60, 120, 200, 240일 이동평균을 각각 계산한다.
     *
     * @param itemPrices 계산 대상 시세 데이터 리스트
     */
    @Transactional
    public void addMa(List<ItemPrice> itemPrices) {
        // 1. 계산 속도를 높이기 위해 시세 데이터에서 종가(Close Price)만 추출하여 별도의 리스트로 만든다.
        List<Double> prices = itemPrices.stream()
                .map(data -> Optional.ofNullable(data.getStck_clpr())
                        .map(Double::valueOf)
                        .orElse(0.0))
                .collect(Collectors.toList());

        int[] movingAverages = {5, 10, 20, 30, 60, 120, 200, 240};

        // 2. 각 시세 데이터(일자)별로 모든 이동평균선을 계산한다.
        for (int i = 0; i < itemPrices.size(); i++) {
            ItemPrice data = itemPrices.get(i);
            for (int ma : movingAverages) {
                // 3. 현재 인덱스(i)를 기준으로 ma 기간만큼의 평균을 계산한다.
                double maValue = calculateMovingAverage(prices, i, ma, itemPrices.size());

                // 4. 계산된 값을 해당 필드에 설정한다.
                switch (ma) {
                    case 5 -> data.setMa5(maValue);
                    case 10 -> data.setMa10(maValue);
                    case 20 -> data.setMa20(maValue);
                    case 30 -> data.setMa30(maValue);
                    case 60 -> data.setMa60(maValue);
                    case 120 -> data.setMa120(maValue);
                    case 200 -> data.setMa200(maValue);
                    case 240 -> data.setMa240(maValue);
                }
            }
            // 5. 변경된 내용을 DB에 반영한다.
            itemPriceRepository.save(data);
        }
    }

    /**
     * 이동평균 값을 계산하는 내부 메서드이다.
     * 현재 인덱스부터 지정된 기간(window)만큼의 데이터를 합산하여 평균을 구한다.
     *
     * @param prices 전체 가격 리스트
     * @param index 현재 계산 기준 인덱스
     * @param window 이동평균 기간 (예: 5일, 20일)
     * @param size 전체 데이터 크기
     * @return 계산된 이동평균 값 (데이터가 부족하면 0.0 반환)
     */
    private static Double calculateMovingAverage(List<Double> prices, int index, int window, int size) {
        double sum = 0.0;
        int count = 0;

        for (int j = 0; j < window; j++) {
            // 리스트 범위를 벗어나지 않는지 확인한다.
            if (index + j < size) {
                sum += prices.get(index + j);
                count++;
            }
        }

        // 데이터가 하나라도 있으면 평균을 반환하고, 아니면 0.0을 반환한다.
        return count > 0 ? sum / count : 0.0;
    }
}