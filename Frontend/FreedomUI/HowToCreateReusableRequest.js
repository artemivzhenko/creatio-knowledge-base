define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "RunButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Run",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.RunRequest",
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

		// --- How to create a reusable request (function-style handler) -------
		// A custom handler can act as a reusable function by:
		//   1. Accepting parameters via the request object
		//   2. Returning a value directly instead of calling next
		//
		// Dispatch it from another handler with executeRequest:
		//   const result = await request.$context.executeRequest({
		//       type: "usr.MyRequest",
		//       $context: request.$context,
		//       param1: value
		//   });
		//
		// Do not call next?.handle in a pure-function request - it is not a
		// platform lifecycle event, so there is nothing to chain to.

		handlers: /**SCHEMA_HANDLERS*/[

			// Caller - dispatches the reusable request and uses its return value
			{
				request: "usr.RunRequest",
				handler: async (request, next) => {
					const name = await request.$context.PDS_Name_h9kddsb;

					const result = await request.$context.executeRequest({
						type: "usr.FormatNameRequest",
						$context: request.$context,
						inputName: name
					});

					request.$context.MyAttribute = result;

					return next?.handle(request);
				}
			},

			// Reusable function - reads request.inputName, returns formatted string
			{
				request: "usr.FormatNameRequest",
				handler: async (request, next) => {
					const input = request.inputName || "";
					return input.trim().toUpperCase();
					// No next?.handle - this is a pure function, not a lifecycle event
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
