package com.weviewcam.client.core.model;

import java.io.Serializable;
import java.util.Date;

public class RecordSegment implements Serializable {
    private int channelNo;
    private Date startTime;
    private Date endTime;
    private String fileName;
    private long fileSize;
    private String recordType; // schedule / alarm / manual / motion

    public RecordSegment() {
        this.recordType = "schedule";
    }

    public RecordSegment(int channelNo, Date startTime, Date endTime, String fileName, long fileSize, String recordType) {
        this.channelNo = channelNo;
        this.startTime = startTime;
        this.endTime = endTime;
        this.fileName = fileName;
        this.fileSize = fileSize;
        this.recordType = recordType != null ? recordType : "schedule";
    }

    public int getChannelNo() {
        return channelNo;
    }

    public void setChannelNo(int channelNo) {
        this.channelNo = channelNo;
    }

    public Date getStartTime() {
        return startTime;
    }

    public void setStartTime(Date startTime) {
        this.startTime = startTime;
    }

    public Date getEndTime() {
        return endTime;
    }

    public void setEndTime(Date endTime) {
        this.endTime = endTime;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public long getFileSize() {
        return fileSize;
    }

    public void setFileSize(long fileSize) {
        this.fileSize = fileSize;
    }

    public String getRecordType() {
        return recordType;
    }

    public void setRecordType(String recordType) {
        this.recordType = recordType;
    }
}
