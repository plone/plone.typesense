import json
import threading

import typesense
from plone import api
from plone.typesense import _, log
from plone.typesense.controlpanels.typesense_controlpanel.controlpanel import (
    ITypesenseControlpanel,
)
from zope.interface import Interface, implementer


class TypesenseError(BaseException):
    def __init__(self, reason, exit_status=1):
        self.reason = reason
        self.exit_status = exit_status

    def __str__(self):
        return "<TypesenseError %r %d>" % (self.reason, self.exit_status)


class ITypesenseConnector(Interface):
    """Marker for TypesenseConnector"""


@implementer(ITypesenseConnector)
class TypesenseConnector:
    """Typesense connection utility"""

    def __init__(self):
        self.data = threading.local()
        self.data.client = None

    @property
    def collection_base_name(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.collection"
        )

    @property
    def get_api_key(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.api_key"
        )

    @property
    def get_timeout(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.timeout"
        )

    @property
    def get_host(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.host"
        )

    @property
    def get_port(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.port"
        )

    @property
    def get_protocol(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.protocol"
        )

    @property
    def get_ts_schema(self):
        return api.portal.get_registry_record(
            "plone.typesense.typesense_controlpanel.ts_schema"
        )

    def get_client(self):
        """ """
        client = getattr(self.data, "client", None)
        if client:
            return client
        api_key = self.get_api_key
        if not api_key:
            raise ValueError(_("No Typesense API key(s) configured"))
        connection_timeout = self.get_timeout
        ts_host = self.get_host
        ts_port = self.get_port
        ts_protocol = self.get_protocol
        self.data.client = typesense.Client(
            {
                "nodes": [
                    {
                        "host": ts_host,  # For Typesense Cloud use xxx.a1.typesense.net
                        "port": int(ts_port),  # For Typesense Cloud use 443
                        "protocol": ts_protocol,  # For Typesense Cloud use https
                    }
                ],
                "api_key": api_key,
                "connection_timeout_seconds": int(connection_timeout) or 300,
            }
        )
        return self.data.client

    def test_connection(self):
        ts = self.get_client()
        try:
            ts.collections.retrieve()
        except typesense.exceptions.ObjectNotFound as exc:
            raise TypesenseError(
                _("Not Found - The requested resource is not found.")
            ) from exc
        except typesense.RequestUnauthorized as exc:
            raise TypesenseError(_("Unauthorized - Your API key is wrong.")) from exc
        except typesense.TypesenseClientError as exc:
            raise TypesenseError(_("Unable to connect :") + "\n\n" + repr(exc)) from exc

    def _get_current_aliased_collection_name(self) -> str:
        """Get the current aliased index name if any"""
        ts = self.get_client()
        current_aliased_index_name = None
        alias = ts.aliases[self.collection_base_name].retrieve()
        if "collection_name" in alias:
            current_aliased_index_name = alias["collection_name"]
        return current_aliased_index_name

    def _get_next_aliased_collection_name(
        self, aliased_index_name: str | None = None
    ) -> str:
        """Get the next aliased index name

        The next aliased collection name is based on the current aliased collection name.
        It's the current aliased collection name incremented by 1.

        :param aliased_index_name: the current aliased index name
        :return: the next aliased index name
        """
        next_version = 1
        if aliased_index_name:
            next_version = int(aliased_index_name.split("-")[-1]) + 1
        return f"{self.collection_base_name}-{next_version}"

    def index(self, objects) -> None:
        """index given objects"""
        ts = self.get_client()
        objects_for_bulk = ""
        for object in objects:
            log.info(f"object: {object}")
            if "uid" in object:
                object["id"] = str(getattr(object, "uid"))
            objects_for_bulk += f"{json.dumps(object)}\n"

        log.info(f"Bulk import objects into {self.collection_base_name}'...")
        res = ts.collections[self.collection_base_name].documents.import_(
            objects_for_bulk, {"action": "create"}
        )
        res = res.split("\n")
        # checks if number of indexed object and object in objects are equal
        if not len(res) == len(objects):
            raise SystemError(
                _(
                    "Unable to index all objects. (indexed: %(indexed)s, "
                    "total: %(total)s)\n%(result)s",
                    indexed=len(res),
                    total=len(objects),
                    result=res,
                )
            )

    def delete(self, uids) -> None:
        """ """
        ts = self._ts_client
        log.info(
            f"Delete uids: {', '.join(uids)} from collection "
            f"'{self.collection_base_name}'."
        )
        ts.collections[self.collection_base_name].documents.delete(
            {"filter_by=id": uids}
        )

    def clear(self) -> None:
        """ """
        ts = self._ts_client
        collection_name = (
            self._get_current_aliased_index_name() or self.collection_base_name
        )
        log.info(f"Clear current_aliased_index_name '{collection_name}'.")
        ts.collections[collection_name].delete()
        # self.settings()

    # def each(self) -> Iterator[dict[str, Any]]:
    #     """ """
    #     ts = self._ts_client
    #     res = ts.collections[self._index_name].documents.search(
    #         {
    #             "q": "*",
    #         }
    #     )
    #     if not res:
    #         # eg: empty index
    #         return
    #     hits = res["hits"]["documents"]
    #     for hit in hits:
    #         yield hit
