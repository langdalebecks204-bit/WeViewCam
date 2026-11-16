# -*- coding: utf-8 -*-
"""
Tests for Excel and CSV import/export and template generation.
"""

import os
import tempfile
import pytest

from core.device_manager import DeviceManager
from core.device_excel_helper import DeviceExcelHelper
from core.base_adapter import DeviceInfo, ChannelInfo, ProtocolType


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


def test_template_generation_excel_and_csv(temp_dir):
    xlsx_path = os.path.join(temp_dir, "template.xlsx")
    csv_path = os.path.join(temp_dir, "template.csv")

    assert DeviceExcelHelper.generate_template_excel(xlsx_path) is True
    assert os.path.exists(xlsx_path) and os.path.getsize(xlsx_path) > 0

    assert DeviceExcelHelper.generate_template_csv(csv_path) is True
    assert os.path.exists(csv_path) and os.path.getsize(csv_path) > 0


def test_import_from_template_and_roundtrip(temp_dir):
    xlsx_path = os.path.join(temp_dir, "template.xlsx")
    DeviceExcelHelper.generate_template_excel(xlsx_path)

    cfg_path = os.path.join(temp_dir, "devices.json")
    dm = DeviceManager(config_path=cfg_path)

    # Import template
    ok, msg, count = dm.import_devices(xlsx_path, overwrite=True)
    assert ok is True
    assert count == 4

    devs = dm.list_devices()
    assert len(devs) == 4

    # Check NVR with 2 channels
    nvr = next((d for d in devs if "192.168.1.100" in d.ip), None)
    assert nvr is not None
    assert len(nvr.channels) == 2
    assert nvr.channels[0].name == "1楼正门大堂"
    assert nvr.channels[1].name == "2楼东侧走廊"

    # Export to Excel and re-import
    exported_xlsx = os.path.join(temp_dir, "exported.xlsx")
    assert dm.export_devices(exported_xlsx) is True

    dm2 = DeviceManager(config_path=os.path.join(temp_dir, "devices2.json"))
    ok2, _, count2 = dm2.import_devices(exported_xlsx, overwrite=True)
    assert ok2 is True
    assert count2 == 4
    nvr2 = next((d for d in dm2.list_devices() if "192.168.1.100" in d.ip), None)
    assert nvr2 is not None
    assert len(nvr2.channels) == 2
    assert nvr2.channels[0].name == "1楼正门大堂"

    # Export to CSV and re-import
    exported_csv = os.path.join(temp_dir, "exported.csv")
    assert dm.export_devices(exported_csv) is True

    dm3 = DeviceManager(config_path=os.path.join(temp_dir, "devices3.json"))
    ok3, _, count3 = dm3.import_devices(exported_csv, overwrite=True)
    assert ok3 is True
    assert count3 == 4
