package me.project.snowbot.dto;

import lombok.Data;

@Data
public class TwoArrData {
    private String rt_cd;
    private String msg_cd;
    private String msg1;
    private String ctx_area_fk100;
    private String ctx_area_nk100;
    private Object[] output1;
    private Object[] output2;
}
