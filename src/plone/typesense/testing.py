# -*- coding: utf-8 -*-
import os

try:
    from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
    HAS_ROBOTFRAMEWORK = True
except ImportError:
    HAS_ROBOTFRAMEWORK = False

from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import plone.typesense


class PloneTypesenseLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.app.dexterity

        self.loadZCML(package=plone.app.dexterity)
        import plone.restapi

        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=plone.typesense)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.typesense:default")


PLONE_TYPESENSE_FIXTURE = PloneTypesenseLayer()


PLONE_TYPESENSE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLONE_TYPESENSE_FIXTURE,),
    name="PloneTypesenseLayer:IntegrationTesting",
)


PLONE_TYPESENSE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONE_TYPESENSE_FIXTURE,),
    name="PloneTypesenseLayer:FunctionalTesting",
)


if HAS_ROBOTFRAMEWORK:
    PLONE_TYPESENSE_ACCEPTANCE_TESTING = FunctionalTesting(
        bases=(
            PLONE_TYPESENSE_FIXTURE,
            REMOTE_LIBRARY_BUNDLE_FIXTURE,
            z2.ZSERVER_FIXTURE,
        ),
        name="PloneTypesenseLayer:AcceptanceTesting",
    )


class PloneTypesenseRealLayer(PloneSandboxLayer):
    """Test layer that connects to a real Typesense server.

    Configured via environment variables:
    - TYPESENSE_HOST (default: localhost)
    - TYPESENSE_PORT (default: 8108)
    - TYPESENSE_API_KEY (default: xyz)
    - TYPESENSE_PROTOCOL (default: http)
    """

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import plone.app.dexterity
        self.loadZCML(package=plone.app.dexterity)
        import plone.restapi
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=plone.typesense)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.typesense:default")

        from plone import api as plone_api

        host = os.environ.get("TYPESENSE_HOST", "localhost")
        port = os.environ.get("TYPESENSE_PORT", "8108")
        api_key = os.environ.get("TYPESENSE_API_KEY", "xyz")
        protocol = os.environ.get("TYPESENSE_PROTOCOL", "http")

        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.enabled", True
        )
        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.host", host
        )
        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.port", port
        )
        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.api_key", api_key
        )
        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.protocol", protocol
        )
        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.collection", "test_content"
        )
        plone_api.portal.set_registry_record(
            "plone.typesense.typesense_controlpanel.ts_only_indexes",
            ["Title", "Description", "SearchableText"],
        )


PLONE_TYPESENSE_REAL_FIXTURE = PloneTypesenseRealLayer()

PLONE_TYPESENSE_REAL_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONE_TYPESENSE_REAL_FIXTURE,),
    name="PloneTypesenseRealLayer:FunctionalTesting",
)
