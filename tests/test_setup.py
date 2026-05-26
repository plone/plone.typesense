"""Test plone.typesense installation."""
import pytest

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID


PACKAGE_NAME = "plone.typesense"


class TestSetup:
    """Test installation and setup."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, installer):
        self.portal = portal
        self.installer = installer

    def test_addon_installed(self):
        """Test addon is installed."""
        assert self.installer.is_product_installed(PACKAGE_NAME)

    def test_browserlayer(self):
        """Test browserlayer is registered."""
        # No dedicated browser layer is registered by this add-on yet.
        # from plone.typesense.interfaces import IPloneTypesenseLayer
        # assert IPloneTypesenseLayer in browser_layers
        pass


class TestUninstall:
    """Test uninstallation."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, installer):
        self.portal = portal
        self.installer = installer
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstall_product(PACKAGE_NAME)

    def test_addon_uninstalled(self):
        """Test addon is uninstalled."""
        assert not self.installer.is_product_installed(PACKAGE_NAME)
