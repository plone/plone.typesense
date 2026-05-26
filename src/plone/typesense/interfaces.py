from typing import Dict
from typing import List
from typing import Tuple
from dataclasses import dataclass
from Products.CMFCore.interfaces import IIndexQueueProcessor
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.interface import Interface

class ITypesenseManager(Interface):
    """
    """

class IPloneTypesenseLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class ITypesenseSearchIndexQueueProcessor(IIndexQueueProcessor):
    """Index queue processor for Typesense."""


class IQueryAssembler(Interface):
    """Assembles a Typesense search query from Plone catalog query parameters."""


class IReindexActive(Interface):
    """Marker interface set on the request during a full catalog rebuild."""


class IMappingAdapter(Interface):
    """Adapter that generates a Typesense collection schema from Plone catalog indexes."""

    def get_schema(collection_name=None):
        """Generate a full Typesense collection schema."""

    def get_field_names():
        """Return a set of field names that would be in the schema."""


class IMappingProvider(Interface):
    """Provides additional Typesense field definitions beyond catalog indexes."""

    def get_fields():
        """Return a list of additional Typesense field definitions."""


# Alias for backward compatibility
from plone.typesense.controlpanels.typesense_controlpanel.controlpanel import (
    ITypesenseControlpanel,
)
ITypesenseSettings = ITypesenseControlpanel


@dataclass
class IndexingActions:

    index: Dict[str, dict]
    reindex: Dict[str, dict]
    unindex: Dict[str, dict]
    index_blobs: Dict[str, dict]
    uuid_path: Dict[str, str]

    def __len__(self):
        size = 0
        size += len(self.index)
        size += len(self.reindex)
        size += len(self.unindex)
        return size

    def all(self) -> List[Tuple[str, str, Dict]]:
        all_data = []
        for attr, action in (
            ("index", "index"),
            ("reindex", "update"),
            ("unindex", "delete"),
        ):
            action_data = [
                (uuid, data) for uuid, data in getattr(self, attr, {}).items()
            ]
            if action_data:
                all_data.extend([(action, uuid, data) for uuid, data in action_data])
        return all_data

    # def all_blob_actions(self):
    #     return [(uuid, data) for uuid, data in getattr(self, "index_blobs", {}).items()]
