define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		// --- How to declare viewModel attributes -----------------------------
		// Attributes are the reactive state of the page.
		// All attribute reads in handlers are async - use await.
		//
		// Four kinds:
		//   plain       - arbitrary value, set/read only in handlers
		//   boolean     - with initial value, used to drive visible/readonly
		//   computed    - starts empty, populated by a change handler
		//   PageParameter - bound to a page parameter (not persisted to DB,
		//                   passed between pages via no-code)
		//   DataSource  - bound to a column of an entity DataSource

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {

					// Plain custom attribute - set/read in handlers via request.$context
					"MyAttribute": {},

					// Boolean attribute with initial value - controls visible / readonly
					"IsButtonVisible": {
						"value": true
					},

					// Computed attribute - populated in a handler; initial value is empty
					"ComputedStatusText": {
						"value": ""
					},

					// Page parameter - lives only on the page, not in the DB.
					// Passed via no-code between pages. Can be any Creatio parameter type.
					"PageParameters_a1TextParameter1_788dmty": {
						"modelConfig": {
							"path": "PageParameters.MyTextParameter1"
						}
					},

					// DataSource field - maps to a column of the connected entity.
					// Attribute name pattern: DataSourceName_ColumnName_randomSuffix
					"PDS_Name_h9kddsb": {
						"modelConfig": {
							"path": "PDS.Name"
						}
					}

				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
