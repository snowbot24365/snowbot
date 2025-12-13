package me.project.snowbot.service;

import java.util.List;

import org.springframework.stereotype.Service;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import me.project.snowbot.entity.TradeHistory;
import me.project.snowbot.repository.TradeHistoryRepository;

@RequiredArgsConstructor
@Service
public class TradeHistoryService {
    private final TradeHistoryRepository tradeHistoryRepository;

    public List<TradeHistory> getBoughtItemInfos(String id, String date) {
        return tradeHistoryRepository.findBoungtItemInfos(id, date);
    }

    public TradeHistory getBoughtItemInfo(String id, String date) {
        return tradeHistoryRepository.findBoungtItemInfo(id, date);
    }

    public TradeHistory getSellSWItemInfo(String id, String date) {
        return tradeHistoryRepository.findSellSWItemInfo(id, date);
    }

    public List<TradeHistory> getAllSWSellHistory() {
        return tradeHistoryRepository.findAllSWSellHistory();
    }


    public List<TradeHistory> getSWSellHistoryByItemId(String id) {
        return tradeHistoryRepository.findSWSellHistoryByItemId(id);
    }

    @Transactional
    public void saveHistory(String itemCd, String date, String time, String type, int count, int price, String rmk) {
        TradeHistory tradeHistory = new TradeHistory();
        tradeHistory.setItemCd(itemCd);
        tradeHistory.setTradeDate(date);
        tradeHistory.setTradeHour(time);
        tradeHistory.setTradeType(type);
        tradeHistory.setTradeCount(count);
        tradeHistory.setTradePrice(price);
        tradeHistory.setRmk(rmk);
        tradeHistoryRepository.save(tradeHistory);
    }
}
