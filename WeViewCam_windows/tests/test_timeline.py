# -*- coding: utf-8 -*-
"""
Unit tests for Timeline coordinate and time calculations.
"""

from datetime import datetime, date, time
from core.base_adapter import RecordSegment


def test_timeline_math():
    target_date = date(2026, 9, 15)
    base_dt = datetime.combine(target_date, time(0, 0, 0))

    seg = RecordSegment(
        channel_no=1,
        start_time=datetime(2026, 9, 15, 2, 0, 0),
        end_time=datetime(2026, 9, 15, 4, 30, 0),
        file_name="rec_01.mp4",
        file_size=1000000
    )

    start_sec = (seg.start_time - base_dt).total_seconds()
    end_sec = (seg.end_time - base_dt).total_seconds()

    assert start_sec == 2 * 3600
    assert end_sec == 4.5 * 3600

    # Test coordinate mapping
    view_start_sec = 0.0
    view_duration_sec = 86400.0
    width = 1000.0

    x1 = ((start_sec - view_start_sec) / view_duration_sec) * width
    x2 = ((end_sec - view_start_sec) / view_duration_sec) * width

    assert round(x1, 2) == round((7200 / 86400) * 1000, 2)
    assert round(x2, 2) == round((16200 / 86400) * 1000, 2)
    assert x2 > x1
