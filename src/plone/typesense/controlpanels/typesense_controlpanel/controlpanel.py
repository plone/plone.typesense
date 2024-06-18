# -*- coding: utf-8 -*-
import json

from plone import api
from plone.app.registry.browser.controlpanel import (
    ControlPanelFormWrapper,
    RegistryEditForm,
)
from plone.restapi.controlpanels import RegistryConfigletPanel
from plone.z3cform import layout
from Products.statusmessages.interfaces import IStatusMessage
from plone.typesense.global_utilities.typesense import ITypesenseConnector
from zope.component import getUtility
from z3c.form import button
from zope.component import adapter
from zope.component.hooks import getSite
from zope.interface import Interface

from plone import schema
from plone.typesense import _
from plone.typesense.interfaces import IPloneTypesenseLayer


class ITypesenseControlpanel(Interface):
    enabled = schema.Bool(
        title=_("Typesense integration enabled"),
        default=True,
    )

    collection = schema.TextLine(
        title=_("Name of Typesense collection"),
        default="content",
        required=True,
    )

    api_key = schema.TextLine(
        title=_("Typesense Admin API key"),
        default="",
        required=True,
    )

    host = schema.TextLine(
        title=_(
            "Typesense Host",
        ),
        description=_(
            "",
        ),
        default="localhost",
        required=False,
        readonly=False,
    )

    port = schema.TextLine(
        title=_(
            "Typesense Port",
        ),
        description=_(
            "",
        ),
        default="8108",
        required=False,
        readonly=False,
    )

    protocol = schema.TextLine(
        title=_(
            "Typesense Protocol",
        ),
        description=_(
            "For Typesense Cloud or other external setups use https!",
        ),
        default="http",
        required=False,
        readonly=False,
    )

    timeout = schema.Int(
        title=_(
            "Typesense connection timeout",
        ),
        description=_(
            "Connection timeout in milliseconds",
        ),
        required=False,
        default=300,
        # defaultFactory=get_default_timeout,
        readonly=False,
    )

    ts_schema = schema.JSONField(
        title=_("Typesense Schema"),
        description=_("Enter a JSON-formatted Typesense schema configuration."),
        schema=json.dumps({}, indent=2),
        default={
            "name": None,
            "fields": [
                {"name": "path", "type": "string"},
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string", "infix": True},
                {"name": "description", "type": "string"},
                {"name": "headlines", "type": "string"},
                {"name": "text", "type": "string", "infix": True},
                {"name": "language", "type": "string", "facet": True},
                {"name": "portal_type", "type": "string", "facet": True},
                {"name": "review_state", "type": "string", "facet": True},
                {"name": "subject", "type": "string[]", "facet": True},
                {"name": "created", "type": "string", "facet": False},
                {"name": "modified", "type": "string", "facet": False},
                {"name": "effective", "type": "string", "facet": False},
                {"name": "expires", "type": "string", "facet": False},
                {"name": "document_type_order", "type": "int32"},
                {"name": "_indexed", "type": "string"},
                {"name": "all_paths", "type": "string[]", "facet": False},
            ],
            "default_sorting_field": "document_type_order",
            "token_separators": ["-"],
            "attributesToSnippet": [
                "title",
                "description",
                "text:20",
            ],
            "attributesToHighlight": [
                "title",
                "description",
                "text:20",
            ],
        },
        required=True,
    )

    ts_only_indexes = schema.List(
        title=_(
            u"Typesense only indexes",
        ),
        description=_(
            u"One index name per line.",
        ),
        value_type=schema.TextLine(
            title=u"index",
        ),
        default=["Title", "Description", "SearchableText"],
        required=False,
    )


class TypesenseControlpanel(RegistryEditForm):
    schema = ITypesenseControlpanel
    schema_prefix = "plone.typesense.typesense_controlpanel"
    label = _("Typesense Controlpanel")

    @button.buttonAndHandler(_("Save"), name=None)
    def handleSave(self, action):
        self.save()

    @button.buttonAndHandler(_("Cancel"), name="cancel")
    def handleCancel(self, action):
        super().handleCancel(self, action)

    @button.buttonAndHandler(_("test connection"), name="test_connection")
    def handle_test_connection(self, action):
        """call typesense test connection view
        """
        ts_connector = getUtility(ITypesenseConnector)
        ts_client = ts_connector.get_client()
        status = ""
        try:
            healthy = ts_client.operations.is_healthy()
            if healthy:
                status = "Connection success, Typesense is healthy."
        except Exception as e:
            status = f"Typesense error:\n{e}"

        IStatusMessage(self.request).addStatusMessage(status, "info")
        self.request.response.redirect(self.request.getURL())

    @button.buttonAndHandler(_("clear and rebuild"), name="clear_and_rebuild")
    def handle_clear_and_rebuild(self, action):
        """ clear and rebuild collection from Plone
        """
        portal = api.portal.get()
        ts_connector = getUtility(ITypesenseConnector)
        # ts_client = ts_connector.get_client()
        self.objects = []
        batch_size = 100

        # def _index_object(obj, path):
        #     if not ICatalogAware.providedBy(obj):
        #         return
        #     self.objects.append(obj)
        #     if len(self.objects) >= batch_size:
        #         ts_connector.index(self.objects)
        #         self.objects = []
        #     if len(self.objects) > 0:
        #         ts_connector.index(self.objects)

        # portal.ZopeFindAndApply(portal, search_sub=True, apply_func=_index_object)
        # return self.index()

    # def save(self):
    #     data, errors = self.extractData()
    #     if errors:
    #         self.status = self.formErrorsMessage
    #         return False

    #     self.applyChanges(data)
    #     return True


TypesenseControlpanelView = layout.wrap_form(
    TypesenseControlpanel, ControlPanelFormWrapper
)


@adapter(Interface, IPloneTypesenseLayer)
class TypesenseControlpanelConfigletPanel(RegistryConfigletPanel):
    """Control Panel endpoint"""

    schema = ITypesenseControlpanel
    configlet_id = "typesense_controlpanel-controlpanel"
    configlet_category_id = "Products"
    title = _("Typesense Controlpanel")
    group = ""
    schema_prefix = "plone.typesense.typesense_controlpanel"
