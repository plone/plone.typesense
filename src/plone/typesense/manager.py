from Products.CMFCore.indexing import processQueue
from zope.interface import implementer
from zope.component import getUtility
from ZTUtils.Lazy import LazyMap
from plone.typesense import interfaces, utils
from plone.typesense.result import BrainFactory, TypesenseResult
from plone.typesense.global_utilities.typesense import ITypesenseConnector
from DateTime import DateTime
from Products.CMFPlone.CatalogTool import CatalogTool
from plone import api
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.permissions import AccessInactivePortalContent
from plone.typesense import log


@implementer(interfaces.ITypesenseManager)
class TypesenseManager:
    """
    """

    _catalog: CatalogTool = None

    @property
    def catalog(self):
        return api.portal.get_tool("portal_catalog")

    @property
    def enabled(self):
        try:
            return api.portal.get_registry_record(
                "plone.typesense.typesense_controlpanel.enabled"
            )
        except api.exc.InvalidParameterError:
            value = False
        return value

    @property
    def active(self):
        """Check if Typesense is enabled and the connector is available."""
        if not self.enabled:
            return False
        try:
            connector = getUtility(ITypesenseConnector)
            if not connector.enabled:
                return False
            client = connector.get_client()
            return client.operations.is_healthy()
        except Exception:
            return False

    @property
    def raise_search_exception(self):
        """Whether to raise search exceptions or fall back to catalog."""
        return False

    @property
    def collection_name(self):
        """Get the collection name from the connector."""
        try:
            connector = getUtility(ITypesenseConnector)
            return connector.collection_base_name
        except Exception:
            return "content"

    def _search(self, query, sort=None, start=0, **query_params):
        """Execute a search against Typesense.

        :param query: Typesense search params dict (q, query_by, filter_by, etc.)
        :param sort: sort_by string
        :param start: offset for pagination
        :param query_params: additional search parameters
        :returns: Typesense search response dict
        """
        connector = getUtility(ITypesenseConnector)
        client = connector.get_client()
        collection = connector.collection_base_name

        params = dict(query)

        if "q" not in params:
            params["q"] = "*"

        # If no query_by specified and q is not wildcard, default to common text fields
        if "query_by" not in params and params["q"] != "*":
            ts_only = utils.get_ts_only_indexes()
            if ts_only:
                params["query_by"] = ",".join(ts_only)
            else:
                params["query_by"] = "Title,Description,SearchableText"

        if sort:
            params["sort_by"] = sort

        if start:
            params["page"] = (start // self.bulk_size) + 1

        params["per_page"] = self.bulk_size

        # Add highlight params if enabled
        highlight_params = self._get_highlight_params()
        if highlight_params:
            params.update(highlight_params)

        # Merge additional query params
        params.update(query_params)

        log.debug(f"Typesense search params: {params}")

        result = client.collections[collection].documents.search(params)
        return result

    def _get_highlight_params(self):
        """Return Typesense highlight parameters if highlighting is enabled."""
        if not self.highlight:
            return {}
        return {
            "highlight_full_fields": "Title,Description,SearchableText",
            "highlight_affix_num_tokens": 4,
        }

    def get_record_by_path(self, path: str) -> dict:
        """Retrieve a document from Typesense by its path."""
        try:
            connector = getUtility(ITypesenseConnector)
            client = connector.get_client()
            collection = connector.collection_base_name
            result = client.collections[collection].documents.search({
                "q": "*",
                "filter_by": f"path:=`{path}`",
                "per_page": 1,
            })
            hits = result.get("hits", [])
            if hits:
                return hits[0].get("document", {})
        except Exception:
            log.error(f"Error getting record by path: {path}", exc_info=True)
        return {}

    @property
    def bulk_size(self) -> int:
        """Bulk size of TypeSense calls."""
        try:
            value = api.portal.get_registry_record(
                "bulk_size", interfaces.ITypesenseSettings, 50
            )
        except KeyError:
            value = 50
        return value

    @property
    def highlight(self):
        """Is search highlighting enabled in the control panel."""
        try:
            value = api.portal.get_registry_record(
                "highlight", interfaces.ITypesenseSettings, False
            )
        except KeyError:
            value = False
        return value

    @property
    def highlight_threshold(self):
        """Threshold for highlight fragment length."""
        return 500

    def search(self, query: dict, factory=None, **query_params) -> LazyMap:
        """
        @param query: The Plone query
        @param factory: The factory that maps each typesense search result.
            By default, get the plone catalog brain.
        @param query_params: Parameters to pass to the search method
            'stored_fields': the list of fields to get from stored source
        """
        factory = BrainFactory(self)
        result = TypesenseResult(self, query, **query_params)
        return LazyMap(factory, result, result.count)

    def search_results(self, request=None, check_perms=False, **kw):
        # Make sure any pending index tasks have been processed
        processQueue()
        if not (self.active and utils.get_ts_only_indexes().intersection(kw.keys())):
            method = (
                self.catalog._old_searchResults
                if check_perms
                else self.catalog._old_unrestrictedSearchResults
            )
            return method(request, **kw)

        query = request.copy() if isinstance(request, dict) else {}
        query.update(kw)

        if check_perms:
            show_inactive = query.get("show_inactive", False)
            if isinstance(request, dict) and not show_inactive:
                show_inactive = "show_inactive" in request

            user = api.user.get_current()
            query["allowedRolesAndUsers"] = self.catalog._listAllowedRolesAndUsers(user)

            if not show_inactive and not _checkPermission(
                AccessInactivePortalContent, self.catalog
            ):
                query["effectiveRange"] = DateTime()
        orig_query = query.copy()
        log.debug(f"Running query: {orig_query}")
        try:
            return self.search(query)
        except Exception:  # NOQA W0703
            if self.raise_search_exception is True:
                raise
            log.error(f"Error running Query: {orig_query}", exc_info=True)
            return self.catalog._old_searchResults(request, **kw)
