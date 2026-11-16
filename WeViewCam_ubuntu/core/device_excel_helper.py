# -*- coding: utf-8 -*-
"""
Device Excel and CSV Import/Export Helper.
Supports:
- Export devices and channels to Excel (.xlsx) and CSV (.csv).
- Import devices and channels from Excel (.xlsx/.xls) and CSV (.csv).
- Generate standardized, friendly import templates for batch onboarding.
"""

import csv
import io
import os
from typing import List, Dict, Any, Tuple, Optional

from core.logger import get_logger

logger = get_logger("DeviceExcelHelper")

# Standard Column Names (Chinese display & friendly mapping)
COL_DEV_NAME = "设备名称*"
COL_DEV_IP = "设备IP*"
COL_PORT = "管理端口"
COL_PROTOCOL = "协议类型"
COL_USERNAME = "登录账号*"
COL_PASSWORD = "登录密码*"
COL_CHANNEL_NO = "通道号(选填)"
COL_CHANNEL_NAME = "通道名称(选填)"
COL_CHANNEL_ENABLED = "是否启用"
COL_RTSP_PORT = "RTSP端口(选填)"

TEMPLATE_HEADERS = [
    COL_DEV_NAME,
    COL_DEV_IP,
    COL_PORT,
    COL_PROTOCOL,
    COL_USERNAME,
    COL_PASSWORD,
    COL_CHANNEL_NO,
    COL_CHANNEL_NAME,
    COL_CHANNEL_ENABLED,
    COL_RTSP_PORT
]

TEMPLATE_SAMPLE_ROWS = [
    [
        "示例1: 办公楼海康NVR",
        "192.168.1.100",
        "8000",
        "hikvision",
        "admin",
        "Abc12345",
        "1",
        "1楼正门大堂",
        "是",
        "554"
    ],
    [
        "示例1: 办公楼海康NVR",
        "192.168.1.100",
        "8000",
        "hikvision",
        "admin",
        "Abc12345",
        "2",
        "2楼东侧走廊",
        "是",
        "554"
    ],
    [
        "示例2: 仓库大华NVR(整机导入/免填通道)",
        "192.168.1.101",
        "37777",
        "dahua",
        "admin",
        "Admin@888",
        "",
        "",
        "",
        "554"
    ],
    [
        "示例3: 独立ONVIF摄像头",
        "192.168.1.102",
        "80",
        "onvif",
        "admin",
        "Admin123",
        "1",
        "地库西入口",
        "是",
        "554"
    ],
    [
        "示例4: 标准RTSP流摄像头",
        "192.168.1.103",
        "554",
        "rtsp",
        "admin",
        "Admin123",
        "1",
        "周界红外相机",
        "是",
        "554"
    ]
]


class DeviceExcelHelper:
    """Utility class for CSV/Excel data conversion and template generation."""

    @staticmethod
    def generate_template_csv(file_path: str) -> bool:
        """Generate a standard CSV template file with instructions and samples."""
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(TEMPLATE_HEADERS)
                for r in TEMPLATE_SAMPLE_ROWS:
                    writer.writerow(r)
            return True
        except Exception as e:
            logger.error(f"生成 CSV 导入模板失败: {e}")
            return False

    @staticmethod
    def generate_template_excel(file_path: str) -> bool:
        """Generate a standard Excel (.xlsx) template file with styling and comments."""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "设备与通道导入模板"

            # Header styling
            header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            sample_font = Font(name="微软雅黑", size=10)
            center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
            left_align = Alignment(horizontal="left", vertical="center")
            thin_border = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )

            # Write header
            ws.append(TEMPLATE_HEADERS)
            ws.row_dimensions[1].height = 28
            for col_num in range(1, len(TEMPLATE_HEADERS) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align

            # Write samples
            for r_idx, row_data in enumerate(TEMPLATE_SAMPLE_ROWS, start=2):
                ws.append(row_data)
                ws.row_dimensions[r_idx].height = 22
                for col_num in range(1, len(row_data) + 1):
                    cell = ws.cell(row=r_idx, column=col_num)
                    cell.font = sample_font
                    cell.border = thin_border
                    if col_num in (3, 7, 9, 10):  # Port, Channel, Enabled, RTSP
                        cell.alignment = center_align
                    else:
                        cell.alignment = left_align

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    # Double width for CJK
                    val_len = sum(2 if ord(c) > 127 else 1 for c in val_str)
                    if val_len > max_len:
                        max_len = val_len
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            # Add instruction sheet
            ws_readme = wb.create_sheet(title="填写说明与规范")
            ws_readme.views.sheetView[0].showGridLines = True
            readme_lines = [
                ("📋 WeViewCam 批量导入设备与通道数据填写指南", ""),
                ("", ""),
                ("1. 必填字段", "设备名称*、设备IP*、登录账号*、登录密码* 为必填项。"),
                ("2. 端口与协议", "管理端口若留空：海康默认 8000，大华默认 37777，ONVIF默认 80，RTSP默认 554。"),
                ("3. 协议支持类型", "支持填写: hikvision (或海康)、dahua (或大华)、onvif、rtsp。"),
                ("4. 通道填写模式 (两种均支持)", ""),
                ("   - 模式一【单通道一行 (推荐)】", "同一台 NVR 可多行填写（保持设备名称和IP相同），每行填写一个通道号及自定义名称。"),
                ("   - 模式二【仅录入整机】", "初期若未知通道明细，通道号和名称可留空！系统导入后，联网自动探查拉取该 NVR 物理通道。"),
                ("5. 是否启用", "选填：填'是'/'1'/'启用'表示开启；填'否'/'0'/'停用'表示禁用该通道。默认为启用。"),
                ("6. 安全提示", "本文件仅供您本地批量导入使用，不会上传任何外部云端，请妥善保管好您的设备密码。")
            ]
            for r_line in readme_lines:
                ws_readme.append(list(r_line))
            ws_readme.column_dimensions['A'].width = 30
            ws_readme.column_dimensions['B'].width = 80
            ws_readme.cell(row=1, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="1F497D")

            wb.save(file_path)
            return True
        except ImportError:
            # Fallback to CSV if openpyxl is not installed
            logger.warning("openpyxl 未安装，自动降级为生成 CSV 模板")
            csv_path = os.path.splitext(file_path)[0] + ".csv"
            return DeviceExcelHelper.generate_template_csv(csv_path)
        except Exception as e:
            logger.error(f"生成 Excel 导入模板失败: {e}")
            return False

    @staticmethod
    def export_devices_to_csv(file_path: str, devices_data: List[Dict[str, Any]]) -> bool:
        """Export device list to CSV format."""
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(TEMPLATE_HEADERS)

                for dev in devices_data:
                    d_name = dev.get("name", "")
                    d_ip = dev.get("ip", "")
                    d_port = dev.get("port", 8000)
                    d_proto = dev.get("protocol", "hikvision")
                    d_user = dev.get("username", "")
                    d_pwd = dev.get("password", "")
                    d_rtsp = dev.get("rtsp_port", 554)
                    channels = dev.get("channels", [])

                    if not channels:
                        writer.writerow([d_name, d_ip, d_port, d_proto, d_user, d_pwd, "", "", "", d_rtsp])
                    else:
                        for ch in channels:
                            ch_no = ch.get("channel_no", "")
                            ch_name = ch.get("name", "")
                            ch_en = "是" if ch.get("is_enabled", True) else "否"
                            writer.writerow([d_name, d_ip, d_port, d_proto, d_user, d_pwd, ch_no, ch_name, ch_en, d_rtsp])
            return True
        except Exception as e:
            logger.error(f"导出 CSV 失败: {e}")
            return False

    @staticmethod
    def export_devices_to_excel(file_path: str, devices_data: List[Dict[str, Any]]) -> bool:
        """Export device list to Excel (.xlsx) with both overview and channel detail sheets."""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            # Sheet 1: Detailed Channels
            ws_ch = wb.active
            ws_ch.title = "通道明细表"

            # Styling
            header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            row_font = Font(name="微软雅黑", size=10)
            center_align = Alignment(horizontal="center", vertical="center")
            left_align = Alignment(horizontal="left", vertical="center")
            thin_border = Border(
                left=Side(style='thin', color='E0E0E0'),
                right=Side(style='thin', color='E0E0E0'),
                top=Side(style='thin', color='E0E0E0'),
                bottom=Side(style='thin', color='E0E0E0')
            )

            ws_ch.append(TEMPLATE_HEADERS)
            ws_ch.row_dimensions[1].height = 26
            for col_idx in range(1, len(TEMPLATE_HEADERS) + 1):
                cell = ws_ch.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align

            row_counter = 2
            for dev in devices_data:
                d_name = dev.get("name", "")
                d_ip = dev.get("ip", "")
                d_port = dev.get("port", 8000)
                d_proto = dev.get("protocol", "hikvision")
                d_user = dev.get("username", "")
                d_pwd = dev.get("password", "")
                d_rtsp = dev.get("rtsp_port", 554)
                channels = dev.get("channels", [])

                if not channels:
                    row_vals = [d_name, d_ip, d_port, d_proto, d_user, d_pwd, "", "", "", d_rtsp]
                    ws_ch.append(row_vals)
                    ws_ch.row_dimensions[row_counter].height = 20
                    for c_idx in range(1, len(row_vals) + 1):
                        cell = ws_ch.cell(row=row_counter, column=c_idx)
                        cell.font = row_font
                        cell.border = thin_border
                        cell.alignment = center_align if c_idx in (3, 7, 9, 10) else left_align
                    row_counter += 1
                else:
                    for ch in channels:
                        ch_no = ch.get("channel_no", "")
                        ch_name = ch.get("name", "")
                        ch_en = "是" if ch.get("is_enabled", True) else "否"
                        row_vals = [d_name, d_ip, d_port, d_proto, d_user, d_pwd, ch_no, ch_name, ch_en, d_rtsp]
                        ws_ch.append(row_vals)
                        ws_ch.row_dimensions[row_counter].height = 20
                        for c_idx in range(1, len(row_vals) + 1):
                            cell = ws_ch.cell(row=row_counter, column=c_idx)
                            cell.font = row_font
                            cell.border = thin_border
                            cell.alignment = center_align if c_idx in (3, 7, 9, 10) else left_align
                        row_counter += 1

            for col in ws_ch.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    val_len = sum(2 if ord(c) > 127 else 1 for c in val_str)
                    if val_len > max_len:
                        max_len = val_len
                ws_ch.column_dimensions[col_letter].width = max(max_len + 4, 12)

            # Sheet 2: Device Overview Summary
            ws_dev = wb.create_sheet(title="设备汇总清单")
            dev_headers = ["设备名称", "设备IP", "管理端口", "协议类型", "登录账号", "通道数量", "RTSP端口"]
            ws_dev.append(dev_headers)
            ws_dev.row_dimensions[1].height = 26
            for col_idx in range(1, len(dev_headers) + 1):
                cell = ws_dev.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = PatternFill(start_color="244061", end_color="244061", fill_type="solid")
                cell.alignment = center_align

            for r_idx, dev in enumerate(devices_data, start=2):
                ch_count = len(dev.get("channels", []))
                row_vals = [
                    dev.get("name", ""),
                    dev.get("ip", ""),
                    dev.get("port", 8000),
                    dev.get("protocol", "hikvision"),
                    dev.get("username", ""),
                    f"{ch_count} 路" if ch_count > 0 else "未探测",
                    dev.get("rtsp_port", 554)
                ]
                ws_dev.append(row_vals)
                ws_dev.row_dimensions[r_idx].height = 20
                for c_idx in range(1, len(row_vals) + 1):
                    cell = ws_dev.cell(row=r_idx, column=c_idx)
                    cell.font = row_font
                    cell.border = thin_border
                    cell.alignment = center_align if c_idx in (3, 6, 7) else left_align

            for col in ws_dev.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    val_len = sum(2 if ord(c) > 127 else 1 for c in val_str)
                    if val_len > max_len:
                        max_len = val_len
                ws_dev.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(file_path)
            return True
        except ImportError:
            logger.warning("openpyxl 未安装，自动降级为 CSV 格式导出")
            csv_path = os.path.splitext(file_path)[0] + ".csv"
            return DeviceExcelHelper.export_devices_to_csv(csv_path, devices_data)
        except Exception as e:
            logger.error(f"导出 Excel 失败: {e}")
            return False

    @staticmethod
    def parse_table_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse CSV or Excel file and aggregate rows into a list of normalized device dicts.
        Rows sharing the same (ip, port) or device_name are grouped together.
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
            raw_rows = DeviceExcelHelper._read_excel_rows(file_path)
        elif ext in (".csv", ".txt"):
            raw_rows = DeviceExcelHelper._read_csv_rows(file_path)
        else:
            raise ValueError(f"不支持的表格格式: {ext} (仅支持 .xlsx, .csv)")

        if not raw_rows:
            return []

        # Find header index mapping
        header_row = raw_rows[0]
        col_map = DeviceExcelHelper._map_headers(header_row)

        devices_map: Dict[str, Dict[str, Any]] = {}

        for row in raw_rows[1:]:
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue

            name = DeviceExcelHelper._get_val(row, col_map.get("name"), default="").strip()
            ip = DeviceExcelHelper._get_val(row, col_map.get("ip"), default="").strip()

            if not ip and not name:
                continue

            raw_port = DeviceExcelHelper._get_val(row, col_map.get("port"), default="8000")
            port = int(float(raw_port)) if str(raw_port).strip().replace(".", "").isdigit() else 8000

            raw_proto = DeviceExcelHelper._get_val(row, col_map.get("protocol"), default="hikvision").strip().lower()
            proto = DeviceExcelHelper._normalize_protocol(raw_proto)

            username = DeviceExcelHelper._get_val(row, col_map.get("username"), default="admin").strip()
            password = DeviceExcelHelper._get_val(row, col_map.get("password"), default="").strip()

            raw_rtsp = DeviceExcelHelper._get_val(row, col_map.get("rtsp_port"), default="554")
            rtsp_port = int(float(raw_rtsp)) if str(raw_rtsp).strip().replace(".", "").isdigit() else 554

            # Channel fields
            raw_ch_no = DeviceExcelHelper._get_val(row, col_map.get("channel_no"), default="")
            ch_name = DeviceExcelHelper._get_val(row, col_map.get("channel_name"), default="").strip()
            raw_enabled = DeviceExcelHelper._get_val(row, col_map.get("enabled"), default="是").strip()

            # Group key by IP + Port (or Name if IP missing)
            group_key = f"{ip}:{port}" if ip else name

            if group_key not in devices_map:
                devices_map[group_key] = {
                    "name": name or f"设备_{ip}",
                    "ip": ip,
                    "port": port,
                    "protocol": proto,
                    "username": username,
                    "password": password,
                    "rtsp_port": rtsp_port,
                    "channels": []
                }
            else:
                # Update empty credentials/name if previous row had none
                cur = devices_map[group_key]
                if not cur["name"] and name:
                    cur["name"] = name
                if not cur["password"] and password:
                    cur["password"] = password

            # Attach channel if channel_no is specified
            if str(raw_ch_no).strip():
                try:
                    ch_no = int(float(raw_ch_no))
                    is_en = raw_enabled not in ("否", "0", "false", "False", "停用", "禁用")
                    # Check if channel already appended
                    existing_nos = {c["channel_no"] for c in devices_map[group_key]["channels"]}
                    if ch_no not in existing_nos:
                        devices_map[group_key]["channels"].append({
                            "channel_no": ch_no,
                            "name": ch_name or f"通道 {ch_no}",
                            "is_enabled": is_en,
                            "is_online": True,
                            "is_ptz": False
                        })
                except Exception:
                    pass

            # Support inline channel list summary (e.g. "1:大门, 2:仓库, 3:财务室, 4:出入口" or semicolon separated)
            raw_summary = DeviceExcelHelper._get_val(row, col_map.get("channels_summary"), default="")
            if str(raw_summary).strip():
                items = [it.strip() for it in str(raw_summary).replace("，", ",").replace("；", ",").replace(";", ",").replace("\n", ",").split(",") if it.strip()]
                for it in items:
                    if ":" in it:
                        parts = it.split(":", 1)
                    elif "：" in it:
                        parts = it.split("：", 1)
                    elif "-" in it:
                        parts = it.split("-", 1)
                    else:
                        parts = [it, f"通道 {it}"]
                    try:
                        c_no = int(float(parts[0].strip()))
                        c_nm = parts[1].strip() if len(parts) > 1 else f"通道 {c_no}"
                        existing_nos = {c["channel_no"] for c in devices_map[group_key]["channels"]}
                        if c_no not in existing_nos:
                            devices_map[group_key]["channels"].append({
                                "channel_no": c_no,
                                "name": c_nm,
                                "is_enabled": True,
                                "is_online": True,
                                "is_ptz": False
                            })
                    except Exception:
                        pass

        return list(devices_map.values())

    @staticmethod
    def _read_excel_rows(file_path: str) -> List[List[Any]]:
        """Read all rows from the active or matching sheet of an Excel file."""
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
        # Prefer '通道明细表' or '设备清单' or active sheet
        sheet = None
        for s_name in ["通道明细表", "设备清单", "Sheet1"]:
            if s_name in wb.sheetnames:
                sheet = wb[s_name]
                break
        if sheet is None:
            sheet = wb.active

        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append(list(row))
        return rows

    @staticmethod
    def _read_csv_rows(file_path: str) -> List[List[str]]:
        """Read CSV rows with robust encoding detection."""
        with open(file_path, "rb") as f:
            raw = f.read()

        # Detect UTF-16 vs UTF-8-SIG vs GBK/GB18030
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            text = raw.decode("utf-16", errors="replace")
        else:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("gb18030", errors="replace")

        reader = csv.reader(io.StringIO(text))
        return list(reader)

    @staticmethod
    def _map_headers(header_row: List[Any]) -> Dict[str, int]:
        """Fuzzy match column header names to standard keys."""
        mapping: Dict[str, int] = {}
        for idx, col in enumerate(header_row):
            if col is None:
                continue
            name = str(col).strip().lower()

            if any(k in name for k in ["设备名", "device_name", "设备名称", "name"]):
                if "name" not in mapping:
                    mapping["name"] = idx
            elif any(k in name for k in ["设备ip", "ip地址", "ip_address", "ip"]):
                if "ip" not in mapping:
                    mapping["ip"] = idx
            elif any(k in name for k in ["管理端口", "设备端口", "port"]) and "rtsp" not in name:
                if "port" not in mapping:
                    mapping["port"] = idx
            elif any(k in name for k in ["协议", "protocol", "类型"]):
                if "protocol" not in mapping:
                    mapping["protocol"] = idx
            elif any(k in name for k in ["账号", "用户名", "user", "username"]):
                if "username" not in mapping:
                    mapping["username"] = idx
            elif any(k in name for k in ["密码", "password", "pwd"]):
                if "password" not in mapping:
                    mapping["password"] = idx
            elif any(k in name for k in ["通道号", "channel_no", "通道id"]):
                if "channel_no" not in mapping:
                    mapping["channel_no"] = idx
            elif any(k in name for k in ["通道明细", "通道列表", "channels_detail", "channels_summary", "通道信息"]):
                if "channels_summary" not in mapping:
                    mapping["channels_summary"] = idx
            elif any(k in name for k in ["通道名", "通道名称", "channel_name"]):
                if "channel_name" not in mapping:
                    mapping["channel_name"] = idx
            elif any(k in name for k in ["启用", "是否启用", "enabled", "状态"]):
                if "enabled" not in mapping:
                    mapping["enabled"] = idx
            elif any(k in name for k in ["rtsp"]):
                if "rtsp_port" not in mapping:
                    mapping["rtsp_port"] = idx
        return mapping

    @staticmethod
    def _get_val(row: List[Any], idx: Optional[int], default: Any = "") -> Any:
        if idx is not None and 0 <= idx < len(row):
            val = row[idx]
            return val if val is not None else default
        return default

    @staticmethod
    def _normalize_protocol(val: str) -> str:
        if "海康" in val or "hik" in val:
            return "hikvision"
        if "大华" in val or "dahua" in val:
            return "dahua"
        if "onvif" in val:
            return "onvif"
        if "rtsp" in val:
            return "rtsp"
        return "hikvision"
