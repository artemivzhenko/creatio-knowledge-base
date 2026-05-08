define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to bind viewModel attributes to UI elements -----------------
		// Use "$AttributeName" to bind any element property to a viewModel attribute.
		// Use "$AttributeName | ConverterName" to transform the value before rendering.
		//
		// Common bindable properties:
		//   value    - field value (two-way binding)
		//   visible  - show/hide the element (boolean attribute)
		//   readonly - make the field read-only (boolean attribute)
		//   disabled - disable the element (boolean attribute)
		//   caption  - dynamic label text (string attribute)

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Input bound to a DataSource field; readonly controlled by a boolean attribute
			{
				"operation": "insert",
				"name": "NameField",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 2, "rowSpan": 1 },
					"type": "crt.Input",
					"label": "$NameField_label",
					"labelPosition": "auto",
					"value": "$PDS_Name_h9kddsb",
					"readonly": "$IsFormReadonly"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 0
			},

			// Button with visibility controlled by a boolean attribute
			{
				"operation": "insert",
				"name": "ActionButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 2, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Submit",
					"iconPosition": "only-text",
					"visible": "$IsButtonVisible",
					// Bind with built-in converter to invert the boolean
					"disabled": "$IsFormReadonly | crt.InvertBooleanValue",
					"clicked": {
						"request": "usr.SubmitRequest",
						"params": {}
					}
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 1
			},

			// Label with dynamic caption and conditional visibility
			{
				"operation": "insert",
				"name": "StatusLabel",
				"values": {
					"layoutConfig": { "column": 1, "row": 3, "colSpan": 2, "rowSpan": 1 },
					"type": "crt.Label",
					"caption": "$ComputedStatusText",
					"visible": "$IsStatusVisible"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 2
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					"PDS_Name_h9kddsb":   { "modelConfig": { "path": "PDS.Name" } },
					"IsFormReadonly":     { "value": false },
					"IsButtonVisible":    { "value": true },
					"IsStatusVisible":    { "value": false },
					"ComputedStatusText": { "value": "" }
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
