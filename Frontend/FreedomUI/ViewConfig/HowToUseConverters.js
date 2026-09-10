define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to use converters -------------------------------------------
		// Converters transform an attribute value before it reaches a UI element.
		// Reference them in viewConfigDiff as: "$AttributeName | ConverterName"
		//
		// Built-in converters (no declaration needed):
		//   crt.InvertBooleanValue        - flips true/false
		//   crt.ToDataTableSortingConfig  - used by data grid sorting
		//
		// Custom converters are declared in the converters section and can be
		// referenced by their key name.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Built-in converter: invert a boolean to drive readonly
			{
				"operation": "insert",
				"name": "NameField",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 2, "rowSpan": 1 },
					"type": "crt.Input",
					"value": "$PDS_Name_h9kddsb",
					// IsEditable = true means the field should NOT be readonly
					"readonly": "$IsEditable | crt.InvertBooleanValue"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 0
			},

			// Custom converter: display boolean as "Yes" / "No"
			{
				"operation": "insert",
				"name": "StatusLabel",
				"values": {
					"layoutConfig": { "column": 1, "row": 2, "colSpan": 2, "rowSpan": 1 },
					"type": "crt.Label",
					"caption": "$IsActive | usr.BoolToYesNo"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 1
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					"PDS_Name_h9kddsb": { "modelConfig": { "path": "PDS.Name" } },
					"IsEditable":       { "value": true },
					"IsActive":         { "value": false }
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,

		// Custom converter - receives the attribute value, returns the display value
		converters: /**SCHEMA_CONVERTERS*/{
			"usr.BoolToYesNo": function(value) {
				return value ? "Yes" : "No";
			}
		}/**SCHEMA_CONVERTERS*/,

		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
