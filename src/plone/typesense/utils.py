from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from plone.typesense.controlpanels.typesense_controlpanel.controlpanel import ITypesenseControlpanel


def get_settings():
    """Return ITypesenseControlpanel values."""
    registry = getUtility(IRegistry)
    try:
        settings = registry.forInterface(ITypesenseControlpanel, check=False)
    except Exception:  # noQA
        settings = None
    return settings


def get_ts_only_indexes():
    """
    """
    settings = get_settings()
    try:
        indexes = settings.ts_only_indexes
        return set(indexes) if indexes else set()
    except (KeyError, AttributeError):
        return ["Title", "Description", "SearchableText"]
