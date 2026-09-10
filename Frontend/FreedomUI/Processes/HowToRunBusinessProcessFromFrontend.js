define("YourPageSchema", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "RunProcessButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Run process",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.RunProcessRequest",
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

		// --- How to run a business process from the frontend -----------------
		// Use sdk.HandlerChainService with crt.RunBusinessProcessRequest to invoke
		// a server-side business process and read its output parameters.
		//
		// processName            - code of the process in Creatio
		// processParameters      - key-value input parameters for the process
		// resultParameterNames   - list of output parameter names to retrieve
		//
		// result.success                       - true if the process completed
		// result.resultParameterValues.ParamName - value of an output parameter
		//
		// Requires: @creatio-devkit/common in SCHEMA_DEPS (sdk argument).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.RunProcessRequest",
				handler: async (request, next) => {
					const handlerChain = sdk.HandlerChainService.instance;

					const field1 = await request.$context.PDS_Field1_someAttr;
					const field2 = await request.$context.PDS_Field2_someAttr;

					const result = await handlerChain.process({
						type: "crt.RunBusinessProcessRequest",
						$context: request.$context,
						processName: "UsrMyProcessCode",
						processParameters: {
							MyField1: field1,
							MyField2: field2
						},
						resultParameterNames: ["MyResultParam", "MySuccessFlag"]
					});

					if (result.success) {
						const output = result.resultParameterValues.MyResultParam;
						request.$context.MyAttribute = output;
					}

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
