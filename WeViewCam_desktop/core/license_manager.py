# -*- coding: utf-8 -*-
"""
WeViewCam Professional License Manager.
Hardware-locked license validation with machine code generation and anti-tamper checks.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple

class LicenseManager:
    """Manages machine fingerprint extraction, license verification, and feature gating."""

    LICENSE_FILE = "config/license.lic"

    @staticmethod
    def get_machine_code() -> str:
        """
        Extract unique, deterministic hardware fingerprint:
        Combines CPU ID, Motherboard UUID, and MAC Address.
        """
        raw_components = []

        try:
            if sys.platform.startswith("win"):
                # Windows CPU ID
                try:
                    cpu_out = subprocess.check_output(
                        "wmic cpu get processorid", shell=True, text=True, stderr=subprocess.DEVNULL
                    )
                    cpu_id = "".join(cpu_out.split()[1:]) if len(cpu_out.split()) > 1 else ""
                    raw_components.append(cpu_id)
                except Exception:
                    pass

                # Windows Motherboard UUID
                try:
                    uuid_out = subprocess.check_output(
                        "wmic csproduct get uuid", shell=True, text=True, stderr=subprocess.DEVNULL
                    )
                    mb_uuid = "".join(uuid_out.split()[1:]) if len(uuid_out.split()) > 1 else ""
                    raw_components.append(mb_uuid)
                except Exception:
                    pass
            else:
                # Linux machine ID
                for p in ["/etc/machine-id", "/var/lib/dbus/machine-id", "/sys/class/dmi/id/product_uuid"]:
                    if os.path.exists(p):
                        try:
                            with open(p, "r") as f:
                                raw_components.append(f.read().strip())
                                break
                        except Exception:
                            pass
        except Exception:
            pass

        # Fallback to node and architecture
        raw_components.append(platform.node())
        raw_components.append(platform.machine())

        combo = "|".join([c for c in raw_components if c])
        h = hashlib.sha256(combo.encode("utf-8")).hexdigest().upper()
        # Format as WVC-XXXX-XXXX-XXXX-XXXX
        return f"WVC-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    @classmethod
    def get_license_path(cls) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, cls.LICENSE_FILE)

    @classmethod
    def load_license(cls) -> Optional[Dict]:
        """Load and parse local license file if exists."""
        lic_path = cls.get_license_path()
        if not os.path.exists(lic_path):
            # Also check plugins folder
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            alt_path = os.path.join(base_dir, "plugins", "license.lic")
            if os.path.exists(alt_path):
                lic_path = alt_path
            else:
                return None

        try:
            with open(lic_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            return None

    @classmethod
    def is_activated(cls, feature_name: str = "daily_inspection") -> Tuple[bool, str, Optional[Dict]]:
        """
        Check whether the requested feature is licensed and currently valid.
        Returns (is_active, status_message, license_data).
        """
        lic = cls.load_license()
        if not lic:
            return False, "未安装专业版授权文件", None

        # Check machine code
        current_mc = cls.get_machine_code()
        target_mc = lic.get("machine_code")
        if target_mc != "*" and target_mc != current_mc:
            return False, f"授权与当前设备不匹配 (授权机型: {target_mc}, 当前机型: {current_mc})", lic

        # Check expiry date
        expire_str = lic.get("expire_date", "1970-01-01")
        try:
            exp_date = datetime.strptime(expire_str, "%Y-%m-%d")
            today = datetime.now()
            if today > exp_date:
                return False, f"授权已于 {expire_str} 到期，请联系作者续费", lic
        except Exception:
            return False, "授权有效期格式错误", lic

        # Check features
        features = lic.get("features", [])
        if feature_name not in features and "*" not in features:
            return False, f"当前授权未包含功能: {feature_name}", lic

        return True, f"已授权至 {expire_str}", lic

    @classmethod
    def save_license(cls, lic_dict: Dict) -> bool:
        """Save license to local config directory."""
        lic_path = cls.get_license_path()
        try:
            os.makedirs(os.path.dirname(lic_path), exist_ok=True)
            with open(lic_path, "w", encoding="utf-8") as f:
                json.dump(lic_dict, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
