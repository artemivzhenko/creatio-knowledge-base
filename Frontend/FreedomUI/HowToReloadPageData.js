define("YourPageSchema", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "RefreshButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Refresh",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.ReloadDataRequest",
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

		// --- How to reload / refresh page data -------------------------------
		// Use crt.LoadDataRequest with loadType "reload" to re-fetch data from
		// the server without navigating away from the page.
		//
		// useLastLoadParameters: true - preserves the current filters and sorting.
		//
		// dataSourceName options:
		//   - getPrimaryModelName() - dynamically resolves the main page DataSource
		//   - hardcoded string       - use the exact DataSource name from the schema
		//
		// Useful after a background operation (web service call, process run)
		// that changed the underlying data.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.ReloadDataRequest",
				handler: async (request, next) => {
					// Option 1: reload the primary DataSource dynamically
					const primaryDS = await request.$context.getPrimaryModelName();

					await request.$context.executeRequest({
						type: "crt.LoadDataRequest",
						$context: request.$context,
						config: {
							loadType: "reload",
							useLastLoadParameters: true
						},
						dataSourceName: primaryDS
					});

					// Option 2: reload a specific DataSource by name
					// await request.$context.executeRequest({
					//     type: "crt.LoadDataRequest",
					//     $context: request.$context,
					//     config: {
					//         loadType: "reload",
					//         useLastLoadParameters: true
					//     },
					//     dataSourceName: "ContactDS"
					// });

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
