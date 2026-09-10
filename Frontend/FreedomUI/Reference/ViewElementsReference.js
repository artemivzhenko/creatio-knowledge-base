define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- Reference: view element types (crt.*) ----------------------------
		// Every entry in viewConfigDiff has a "type". This is the catalogue of
		// the types actually used across the packages in this repository, with
		// the properties each one accepts.
		//
		// COMMON PROPERTIES, valid on almost every element:
		//   layoutConfig  { column, row, colSpan, rowSpan }  position in the
		//                 parent grid container; 1-based
		//   visible       boolean or "$Attribute"
		//   readonly      boolean or "$Attribute"
		//   label         "$Resources.Strings.<Key>"
		//   labelPosition "auto" | "above" | "left" | "right"
		//   control       "$AttributeName"  - the bound attribute
		//   placeholder, tooltip
		//   fitContent    boolean - shrink to content instead of filling
		//   visible/readonly accept converter pipes: "$Attr | crt.InvertBooleanValue"
		//
		// LAYOUT (see HowToLayoutPageWithContainers.js)
		//   crt.GridContainer    rows/columns/gap/padding/color/borderRadius
		//   crt.FlexContainer    direction: "column" | "row"
		//   crt.TabPanel         mode "tab", styleType, tab colours
		//   crt.TabContainer     one tab inside a TabPanel
		//   crt.ExpansionPanel   collapsible block: title, expanded, toggleType,
		//                        togglePosition, fullWidthHeader, titleWidth
		//
		// INPUTS
		//   crt.Input            single-line text
		//   crt.NumberInput      numeric
		//   crt.Checkbox         boolean; labelPosition "right" is the norm
		//   crt.DateTimePicker   pickerType: "date" | "time" | "datetime"
		//   crt.ComboBox         lookup / enum; mode "List", listActions,
		//                        controlActions, showValueAsLink
		//   crt.RichTextEditor   formatted text
		//   crt.WebInput         URL
		//   crt.PhoneInput       phone
		//   crt.Slider           numeric range
		//   crt.ButtonToggleGroup  segmented switch
		//   crt.Button           caption, iconPosition, clicked { request, params }
		//
		// DATA
		//   crt.DataGrid         list; see HowToConfigureDataGridAndSummaries.js
		//   crt.Summaries        aggregate row under a grid
		//   crt.FileList         attachments; see HowToUploadAndShowFiles.js
		//   crt.SearchFilter     free-text search over a data source
		//   crt.QuickFilter      date / lookup quick filter
		//
		// WIDGETS
		//   crt.IndicatorWidget       single metric tile
		//   crt.ChartWidget           chart
		//   crt.EntityStageProgressBar  stage bar bound to a stage column
		//   crt.Approval              approvals block
		//   crt.AccountCompactProfile / crt.CommunicationOptions  stock profile blocks
		//   crt.TimelineTile          timeline entry
		//
		// CUSTOM ELEMENTS registered by a Module schema appear with the package
		// prefix instead of crt., e.g. "usr.FrameComponent", "su.CardHeader",
		// "su.Detail". See ClassicUI/Modules/HowToUseCssAndCustomViewElementModules.js
		// for how such an element is registered.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Text input.
			{
				"operation": "insert",
				"name": "NameInput",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Input",
					"label": "$Resources.Strings.PDS_Name_a1b2c3d",
					"labelPosition": "auto",
					"control": "$PDS_Name_a1b2c3d",
					"visible": true,
					"readonly": false,
					"placeholder": "",
					"tooltip": ""
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},

			// Numeric input.
			{
				"operation": "insert",
				"name": "AmountInput",
				"values": {
					"layoutConfig": { "column": 1, "row": 2, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.NumberInput",
					"label": "$Resources.Strings.PDS_Amount_q0lg97k",
					"labelPosition": "auto",
					"control": "$PDS_Amount_q0lg97k"
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 1
			},

			// Lookup / enum. `mode` "List" renders a drop-down; listActions and
			// controlActions add the "+ create" and side actions.
			{
				"operation": "insert",
				"name": "StatusComboBox",
				"values": {
					"layoutConfig": { "column": 1, "row": 3, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.ComboBox",
					"label": "$Resources.Strings.PDS_Status_oschim3",
					"labelPosition": "auto",
					"control": "$PDS_Status_oschim3",
					"mode": "List",
					"listActions": [],
					"controlActions": [],
					"showValueAsLink": true,
					"visible": true,
					"readonly": true,
					"placeholder": "",
					"tooltip": ""
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 2
			},

			// Boolean.
			{
				"operation": "insert",
				"name": "IsUrgentCheckbox",
				"values": {
					"layoutConfig": { "column": 1, "row": 4, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Checkbox",
					"label": "$Resources.Strings.PageParameters_IsUrgent_65otiic",
					"labelPosition": "right",
					"control": "$PageParameters_IsUrgent_65otiic",
					"visible": true,
					"readonly": false
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 3
			},

			// Date / time. pickerType decides which parts are editable.
			{
				"operation": "insert",
				"name": "CloseDatePicker",
				"values": {
					"layoutConfig": { "column": 1, "row": 5, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.DateTimePicker",
					"pickerType": "datetime",
					"label": "$Resources.Strings.PDS_CloseDate_un3gzvs",
					"labelPosition": "auto",
					"control": "$PDS_CloseDate_un3gzvs"
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 4
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
