"""Freedom UI component types -> the element types of the UI test utility's page files (automatic-creatio-tests).

The framework addresses an element by its `element-name`, which is the `name` of the view-config
item (all 11 own controls of a two-tab test page matched what `analyse` wrote). None means the type
depends on the bound column or the control's options (see PageSchema.page_file).
"""

FRAMEWORK_TYPE: dict[str, str | None] = {
    "crt.Input": "Text",
    "crt.RichTextEditor": "RichText",
    "crt.EmailInput": "Email",
    "crt.PhoneInput": "Phone",
    "crt.WebInput": "Link",
    "crt.NumberInput": None,       # Integer for an Integer column, else Decimal
    "crt.DateTimePicker": None,    # pickerType date / time / datetime, else the column's type
    "crt.Checkbox": "Boolean",
    "crt.ComboBox": "Lookup",
    "crt.Button": "Button",
    "crt.TabContainer": "Tab",     # one tab of a tab panel
    "crt.DataGrid": "DataGrid",
    "crt.EntityStageProgressBar": "CasesBar",
    "crt.ButtonToggleGroup": "ToggleTab",
}
PICKER_TYPE = {"date": "Date", "time": "Time", "datetime": "DateTime"}

# What `analyse` found on pages of a template that the page's own schema never lists (the template's elements).
# Read off the analysed pages of the test bed; a page that removes or hides one drops it.
TEMPLATE_ELEMENTS: dict[str, list[dict]] = {
    "PageWithTabsFreedomTemplate": [
        {"code": "AttachmentAddButton", "label": "", "type": "Button"},
        {"code": "AttachmentRefreshButton", "label": "", "type": "Button"},
        {"code": "BackButton", "label": "", "type": "Button"},
        {"code": "CloseButton", "label": "Close", "type": "Button"},
        {"code": "SetRecordRightsButton", "label": "", "type": "Button"},
        {"code": "GeneralInfoTab", "label": "General information", "type": "Tab"},
        {"code": "CardButtonToggleGroup", "label": "", "type": "ToggleTab", "tabs": ["Feed", "Attachments"]},
    ],
}
