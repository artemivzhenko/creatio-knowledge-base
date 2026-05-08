define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "OpenSidebarButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Open sidebar",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.OpenSidebarRequest",
						"params": {}
					}
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to open a sidebar page programmatically ---------------------
		// Use crt.OpenSidebarRequest dispatched via executeRequest.
		//
		// sidebarCode must match the schema code of the sidebar page registered
		// in the application (AppPage or AppSidebarPage schema).
		// $context passes data to the sidebar for binding - can be left empty.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.OpenSidebarRequest",
				handler: async (request, next) => {
					await request.$context.executeRequest({
						type: "crt.OpenSidebarRequest",
						$context: request.$context,
						sidebarCode: "UsrMySidebarPage"
					});

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
