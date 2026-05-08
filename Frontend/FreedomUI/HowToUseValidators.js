define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to use field validators -------------------------------------
		// Validators run on the field value before saving and display an inline
		// error tooltip when the value is invalid.
		//
		// Two parts:
		//   1. Declare the validator type in the "validators" section.
		//   2. Reference it in the attribute's "validators" block in viewModelConfigDiff.
		//
		// Validator function receives a "config" object (the params you passed)
		// and returns a function that receives the field "control".
		// Return null = valid; return an object = invalid (message is shown).
		//
		// "async": false - synchronous validator.
		// "async": true  - async validator (return a Promise).

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "NameField",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 2, "rowSpan": 1 },
					"type": "crt.Input",
					"value": "$PDS_Name_h9kddsb"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					"PDS_Name_h9kddsb": {
						"modelConfig": {
							"path": "PDS.Name"
						},
						// Attach one or more validators to this attribute
						"validators": {
							"ValidateName": {
								"type": "usr.ValidateFieldValue",
								"params": {
									"invalidValue": "Request",
									"message": "This name is not allowed."
								}
							}
						}
					}
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,

		// Validator type declaration
		validators: /**SCHEMA_VALIDATORS*/{
			"usr.ValidateFieldValue": {
				"validator": function(config) {
					return function(control) {
						// Return null = valid; return object = invalid
						return control.value !== config.invalidValue
							? null
							: { "usr.ValidateFieldValue": { message: config.message } };
					};
				},
				"params": [
					{ "name": "invalidValue" },
					{ "name": "message" }
				],
				"async": false
			}
		}/**SCHEMA_VALIDATORS*/

	};
});
