from zope.interface import implementer
from zope.interface import Interface


class ITypesenseConnector(Interface):
    """Marker for TypesenseConnector"""


@implementer(ITypesenseConnector)
class TypesenseConnector:
    """Typesense connection utility"""

    def connect():
        """ """
        import pdb

        pdb.set_trace()  # NOQA: E702
