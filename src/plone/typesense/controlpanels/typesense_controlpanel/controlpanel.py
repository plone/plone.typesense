# -*- coding: utf-8 -*-
from plone import schema
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.restapi.controlpanels import RegistryConfigletPanel
from plone.typesense import _
from plone.typesense.interfaces import IPloneTypesenseLayer
from plone.z3cform import layout
from zope.component import adapter
from zope.interface import Interface

import json


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


class TypesenseControlpanel(RegistryEditForm):
    schema = ITypesenseControlpanel
    schema_prefix = "plone.typesense.typesense_controlpanel"
    label = _("Typesense Controlpanel")


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
