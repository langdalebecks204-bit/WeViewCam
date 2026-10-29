# -*- coding: utf-8 -*-
"""
Test native Windows Hikvision HCNetSDK DLL loading and cleanup.
"""

import os
import sys
import pytest


def test_windows_native_dll_loading():
    """Verify that Windows HCNetSDK.dll and PlayCtrl.dll are discovered and initialized."""
    if not sys.platform.startswith("win"):
        pytest.skip("Windows only test")

    # Temporarily remove HIK_SDK_MOCK to test real DLL load
    old_mock = os.environ.pop("HIK_SDK_MOCK", None)
    try:
        from adapters.hikvision.driver import HCNetSDKLibrary
        HCNetSDKLibrary._instance = None
        sdk = HCNetSDKLibrary.get_instance()
        assert sdk.is_loaded is True
        assert sdk.hcnetsdk is not None
        assert sdk.playctrl is not None
        # Clean up
        sdk.cleanup()
    finally:
        if old_mock is not None:
            os.environ["HIK_SDK_MOCK"] = old_mock
        from adapters.hikvision.driver import HCNetSDKLibrary
        HCNetSDKLibrary._instance = None
