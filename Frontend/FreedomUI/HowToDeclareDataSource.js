define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		// --- How to declare a DataSource in modelConfigDiff ------------------
		// The primary DataSource (PDS) for the main page entity is declared by
		// the platform automatically. Add extra DataSources here when your page
		// needs to load data from additional entities.
		//
		// "scope": "page"        - loads once and lives for the whole page
		// "scope": "viewElement" - loads per element (e.g. a detail grid)
		//
		// Columns declared in "attributes" become available as attributes in
		// viewModelConfigDiff using the path "DataSourceName.ColumnName".

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": [],
				"values": {
					"dataSources": {
						"ContactDS": {
							"type": "crt.EntityDataSource",
							"config": {
								"entitySchemaName": "Contact",
								"attributes": {
									"Name":  { "path": "Name" },
									"Email": { "path": "Email" }
								}
							},
							"scope": "page"
						}
					}
				}
			}
		]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
