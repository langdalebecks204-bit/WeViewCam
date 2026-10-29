# -*- coding: utf-8 -*-
"""
Pytest configuration and global fixtures for WeViewCam Windows tests.
"""

import os
import sys
import pytest

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Ensure tests run in deterministic mock environment without needing physical camera hardware."""
    monkeypatch.setenv("HIK_SDK_MOCK", "1")
    from adapters.hikvision.driver import HCNetSDKLibrary
    HCNetSDKLibrary._instance = None
    yield
    HCNetSDKLibrary._instance = None
