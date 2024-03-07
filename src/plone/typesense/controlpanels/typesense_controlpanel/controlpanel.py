# -*- coding: utf-8 -*-
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.restapi.controlpanels import RegistryConfigletPanel
from plone.typesense import _
from plone.typesense.interfaces import IPloneTypesenseLayer
from plone.z3cform import layout
from zope import schema
from zope.component import adapter
from zope.interface import Interface


class ITypesenseControlpanel(Interface):
    myfield_name = schema.TextLine(
        title=_(
            "This is an example field for this control panel",
        ),
        description=_(
            "",
        ),
        default="",
        required=False,
        readonly=False,
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
