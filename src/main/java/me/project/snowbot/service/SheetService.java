package me.project.snowbot.service;

import me.project.snowbot.dto.SheetData;

public interface SheetService {
    void insert(String id, String cl, SheetData sheetData);
}
