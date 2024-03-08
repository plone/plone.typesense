import typesense
from plone import api
from plone.typesense import _
from plone.typesense.controlpanels.typesense_controlpanel.controlpanel import (
    ITypesenseControlpanel,
)
from zope.interface import Interface, implementer


class ITypesenseConnector(Interface):
    """Marker for TypesenseConnector"""


@implementer(ITypesenseConnector)
class TypesenseConnector:
    """Typesense connection utility"""

    client = None

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

    def get_client(self):
        """ """
        if self.client:
            return self.client
        api_key = self.get_api_key
        if not api_key:
            raise ValueError(_("No Typesense API key(s) configured"))
        connection_timeout = self.get_timeout
        ts_host = self.get_host
        ts_port = self.get_port
        ts_protocol = self.get_protocol
        self.client = typesense.Client(
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
        return self.client
