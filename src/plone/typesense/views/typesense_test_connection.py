# -*- coding: utf-8 -*-

# from plone.typesense import _
from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.interface import Interface


# from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class ITypesenseTestConnection(Interface):
    """Marker Interface for ITypesenseTestConnection"""


@implementer(ITypesenseTestConnection)
class TypesenseTestConnection(BrowserView):
    # If you want to define a template here, please remove the template from
    # the configure.zcml registration of this view.
    # template = ViewPageTemplateFile('typesense_test_connection.pt')

    def __call__(self):
        # Implement your own actions:
        return self.index()
