# -*- coding: utf-8 -*-
"""
Test native Windows vendor SDK (Hikvision and Dahua) DLL loading and cleanup.
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


def test_dahua_windows_native_dll_loading():
    """Verify that Windows Dahua dhnetsdk.dll is discovered and initialized."""
    if not sys.platform.startswith("win"):
        pytest.skip("Windows only test")

    # Temporarily remove DAHUA_SDK_MOCK to test real DLL load
    old_mock = os.environ.pop("DAHUA_SDK_MOCK", None)
    try:
        from adapters.dahua.driver import DahuaSDKLibrary
        DahuaSDKLibrary._instance = None
        sdk = DahuaSDKLibrary.get_instance()
        assert sdk.is_loaded is True
        assert sdk.net_client is not None
        assert sdk.net_client.sdk is not None
        ver = sdk.net_client.sdk.CLIENT_GetSDKVersion()
        assert ver > 0
        # Clean up
        sdk.cleanup()
    finally:
        if old_mock is not None:
            os.environ["DAHUA_SDK_MOCK"] = old_mock
        from adapters.dahua.driver import DahuaSDKLibrary
        DahuaSDKLibrary._instance = None
