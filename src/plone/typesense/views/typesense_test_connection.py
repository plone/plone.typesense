# -*- coding: utf-8 -*-

# from plone.typesense import _
from plone.typesense import log
from plone.typesense.global_utilities.typesense import ITypesenseConnector
from Products.Five.browser import BrowserView
from zope.component import getUtility
from zope.interface import Interface, implementer

# from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class ITypesenseTestConnection(Interface):
    """Marker Interface for ITypesenseTestConnection"""


@implementer(ITypesenseTestConnection)
class TypesenseTestConnection(BrowserView):
    # If you want to define a template here, please remove the template from
    # the configure.zcml registration of this view.
    # template = ViewPageTemplateFile('typesense_test_connection.pt')

    def __call__(self):
        ts_connector = getUtility(ITypesenseConnector)
        ts_client = ts_connector.get_client()
        log.info(ts_client)
        self.status = "connection success"
        return self.index()
