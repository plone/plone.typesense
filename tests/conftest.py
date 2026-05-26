"""Pytest configuration for plone.typesense tests.

``fixtures_factory`` (from pytest-plone) wires each plone.testing layer into a
set of pytest fixtures via zope.pytestlayer, so the layer is actually started.
It produces the ``integration`` / ``functional`` fixtures that pytest-plone's
bundled ``portal``, ``app`` and ``installer`` fixtures depend on.
"""
from pytest_plone import fixtures_factory

from plone.typesense.testing import PLONE_TYPESENSE_FUNCTIONAL_TESTING
from plone.typesense.testing import PLONE_TYPESENSE_INTEGRATION_TESTING


pytest_plugins = ["pytest_plone"]


globals().update(
    fixtures_factory(
        (
            (PLONE_TYPESENSE_FUNCTIONAL_TESTING, "functional"),
            (PLONE_TYPESENSE_INTEGRATION_TESTING, "integration"),
        )
    )
)
