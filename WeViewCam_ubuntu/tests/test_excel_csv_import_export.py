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


def test_incremental_merge_no_duplicate_channels(temp_dir):
    """Verify incremental merge (overwrite=False) never creates duplicate channels with probed offset."""
    cfg_path = os.path.join(temp_dir, "nvr_devices.json")
    dm = DeviceManager(config_path=cfg_path)

    # 1. Pre-populate device with 8 physical probed channels (33..40)
    probed_channels = [
        ChannelInfo(channel_no=ch_no, name=f"IP通道 {i}", is_online=True, is_enabled=True)
        for i, ch_no in enumerate(range(33, 41), start=1)
    ]
    dev = DeviceInfo(
        device_id="nvr-8ch-001",
        name="海康8路NVR",
        ip="192.168.1.188",
        port=8000,
        protocol=ProtocolType.HIKVISION,
        channels=probed_channels
    )
    dm.add_device(dev)

    # Verify initial state: exactly 8 channels (33..40)
    initial_dev = dm.get_device("nvr-8ch-001")
    assert len(initial_dev.channels) == 8
    assert initial_dev.channels[0].channel_no == 33

    # 2. User imports Excel/CSV with channels 1..4 (sequential user indices) using incremental merge
    import_csv = os.path.join(temp_dir, "user_channels.csv")
    with open(import_csv, "w", encoding="utf-8-sig") as f:
        f.write("设备名称,设备IP,管理端口,协议类型,登录账号,登录密码,通道号,通道名称,是否启用,RTSP端口\n")
        f.write("海康8路NVR,192.168.1.188,8000,hikvision,admin,12345,1,正门大堂,是,554\n")
        f.write("海康8路NVR,192.168.1.188,8000,hikvision,admin,12345,2,后门仓库,是,554\n")
        f.write("海康8路NVR,192.168.1.188,8000,hikvision,admin,12345,3,财务室,是,554\n")
        f.write("海康8路NVR,192.168.1.188,8000,hikvision,admin,12345,4,员工食堂,是,554\n")

    # Incremental merge: overwrite=False!
    ok, msg, count = dm.import_devices(import_csv, overwrite=False)
    assert ok is True
    assert count == 1

    merged_dev = dm.get_device("nvr-8ch-001")
    # MUST STILL BE EXACTLY 8 CHANNELS, NOT 12!
    assert len(merged_dev.channels) == 8
    assert [c.channel_no for c in merged_dev.channels] == list(range(33, 41))

    # Channels 33..36 must have the user's custom names
    assert merged_dev.channels[0].name == "正门大堂"
    assert merged_dev.channels[1].name == "后门仓库"
    assert merged_dev.channels[2].name == "财务室"
    assert merged_dev.channels[3].name == "员工食堂"
    # Channels 37..40 keep their probed names
    assert merged_dev.channels[4].name == "IP通道 5"
    assert merged_dev.channels[7].name == "IP通道 8"


def test_import_with_inline_channels_summary(temp_dir):
    """Verify import with inline channels summary column (e.g. 1:大门, 2:仓库)."""
    cfg_path = os.path.join(temp_dir, "summary_devices.json")
    dm = DeviceManager(config_path=cfg_path)

    csv_path = os.path.join(temp_dir, "inline_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("设备名称,设备IP,管理端口,协议类型,登录账号,登录密码,通道明细\n")
        f.write('车间NVR,192.168.2.200,8000,hikvision,admin,pass,"1:生产车间, 2:打包区, 3:发货口"\n')

    ok, msg, count = dm.import_devices(csv_path, overwrite=True)
    assert ok is True
    assert count == 1

    dev = dm.list_devices()[0]
    assert len(dev.channels) == 3
    assert dev.channels[0].channel_no == 1
    assert dev.channels[0].name == "生产车间"
    assert dev.channels[1].channel_no == 2
    assert dev.channels[1].name == "打包区"
    assert dev.channels[2].channel_no == 3
    assert dev.channels[2].name == "发货口"
