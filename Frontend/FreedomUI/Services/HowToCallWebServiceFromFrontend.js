define("YourPageSchema", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "CallServiceButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Call service",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.CallServiceRequest",
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

		// --- How to call a custom web service from the frontend --------------
		// Use sdk.HttpClientService to call Creatio web services (WCF services)
		// from inside a handler.
		//
		// Endpoint format: /rest/ServiceName/MethodName
		//   ServiceName - class name of your C# service (e.g. ContactLookupService)
		//   MethodName  - method decorated with [OperationContract]
		//
		// GET:  httpClientService.get(url)
		// POST: httpClientService.post(url, payload)
		//
		// The response body is in response.body; result is in response.body.MethodNameResult
		// (WCF wraps the return value in a property named "<MethodName>Result").
		//
		// Requires: @creatio-devkit/common in SCHEMA_DEPS (sdk argument).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.CallServiceRequest",
				handler: async (request, next) => {
					const httpClientService = new sdk.HttpClientService();

					// GET request
					const getResponse = await httpClientService.get("/rest/ContactLookupService/GetContactIdByName?name=John");
					const contactId = getResponse?.body?.GetContactIdByNameResult;

					// POST request - payload is serialized to JSON automatically
					const payload = {
						param1: "value1",
						param2: "value2"
					};
					const postResponse = await httpClientService.post("/rest/MyService/MyMethod", payload);
					const postResult = postResponse?.body?.MyMethodResult;

					request.$context.MyAttribute = postResult;

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
