package me.project.snowbot.service;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Service;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.TradeStatus;
import me.project.snowbot.repository.TradeStatusRepository;
import me.project.snowbot.util.CustomDateUtils;

/**
 * 종목별 매매 진행 상태(TradeStatus)를 관리하는 서비스 클래스이다.
 * 주문 접수, 체결, 매도 등 매매의 생명주기 상태를 DB에 기록하고 업데이트하는 역할을 수행한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TradeStatusService {
    private final TradeStatusRepository tradeStatusRepository;

    /**
     * 특정 종목(id)과 날짜(date)에 해당하는 매매 상태 정보를 조회한다.
     *
     * @param id 종목 코드
     * @param date 기준 날짜
     * @return 매매 상태 엔티티 객체
     */
    public TradeStatus getTradeStatus(String id, String date) {
        return tradeStatusRepository.findByStatus(id, date);
    }
    
    /**
     * 특정 날짜에 스윙 전략으로 매수된 종목들의 매매 상태 리스트를 조회한다.
     *
     * @param date 기준 날짜
     * @return 매수된 종목들의 매매 상태 리스트
     */
    public List<TradeStatus> getBoughtSWItem(String date) {
        return tradeStatusRepository.findByBuySWId(date);
    }

    /**
     * 매매 상태 정보를 생성하거나 업데이트한다(Upsert).
     * 기존 데이터가 없으면 주문 번호와 현재 시간을 포함하여 새로 생성하고,
     * 데이터가 있으면 매매 유형, 수량, 가격 정보를 갱신한다.
     *
     * @param id 종목 코드
     * @param date 기준 날짜
     * @param type 매매 유형 (매수접수, 매수체결 등)
     * @param odno 주문 번호
     * @param qty 거래 수량
     * @param rate 수익률 (현재 로직에서는 저장되지 않음)
     * @param price 거래 가격
     */
    @Transactional
    public void updateTradeStatus(String id, String date, String type, String odno, int qty, double rate, int price) {
        // 1. 기존 매매 상태 정보를 조회한다. 데이터가 없으면 새로운 객체를 생성하여 초기화한다.
        TradeStatus tradeStatus = Optional.ofNullable(tradeStatusRepository.findByStatus(id, date))
                .orElseGet(() -> {
                    TradeStatus newTradeStatus = new TradeStatus();
                    newTradeStatus.setItemCd(id);
                    newTradeStatus.setTradeDate(date);
                    // 신규 생성 시 현재 시간을 거래 시간으로 설정한다.
                    newTradeStatus.setTradeTime(CustomDateUtils.getTime());
                    newTradeStatus.setOdno(odno);
                    return newTradeStatus;
                });

        // 2. 매매 유형, 수량, 가격 정보를 설정한다.
        tradeStatus.setTradeType(type);
        tradeStatus.setQty(qty);
        tradeStatus.setTradePrice(price);

        // 3. 변경된 내용을 저장한다.
        tradeStatusRepository.save(tradeStatus);
    }

    /**
     * 특정 종목의 매매 유형(TradeType) 상태만 별도로 수정한다.
     * (예: 매수주문 -> 매수체결 등 상태 변경 시 사용)
     *
     * @param id 종목 코드
     * @param date 기준 날짜
     * @param type 변경할 매매 유형
     */
    @Transactional
    public void updateTradeType(String id, String date, String type) {
        TradeStatus tradeStatus = tradeStatusRepository.findByStatus(id, date);
        if (tradeStatus != null) {
            tradeStatus.setTradeType(type);
            tradeStatusRepository.save(tradeStatus);
        }
    }
}