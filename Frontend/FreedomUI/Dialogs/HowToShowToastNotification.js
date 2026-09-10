define("YourPageSchema", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "NotifyButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Notify",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.ShowToastRequest",
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

		// --- How to show a toast (non-blocking) notification -----------------
		// Use crt.NotificationRequest for lightweight messages that disappear
		// automatically, unlike crt.ShowDialogRequest which requires user action.
		//
		// message  - text to display
		// duration - milliseconds before auto-dismiss (default ~3000)
		//
		// Available since Creatio 8.0.10.
		// No SDK dependency required - dispatched via executeRequest like any other request.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.ShowToastRequest",
				handler: async (request, next) => {
					const name = await request.$context.PDS_Name_someAttr;

					request.$context.executeRequest({
						type: "crt.NotificationRequest",
						$context: request.$context,
						message: "Record saved: " + name
					});

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
