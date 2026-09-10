define("YourPageSchema", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "OpenRecordButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Open record",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.OpenRecordRequest",
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

		// --- How to open a record edit page or create a new record -----------
		// Use sdk.HandlerChainService with crt.UpdateRecordRequest to open an
		// existing record, or crt.CreateRecordRequest to open a blank edit page.
		//
		// crt.UpdateRecordRequest:
		//   entityName - schema name of the entity
		//   recordId   - Guid of the record to open
		//
		// crt.CreateRecordRequest:
		//   entityName    - schema name of the entity
		//   defaultValues - array of { attributeName, value } to pre-fill fields
		//
		// Requires: @creatio-devkit/common in SCHEMA_DEPS (sdk argument).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.OpenRecordRequest",
				handler: async (request, next) => {
					const handlerChain = sdk.HandlerChainService.instance;

					// Open an existing record by id
					const recordId = await request.$context.PDS_ContactId_someAttr;

					await handlerChain.process({
						type: "crt.UpdateRecordRequest",
						$context: request.$context,
						entityName: "Contact",
						recordId: recordId
					});

					return next?.handle(request);
				}
			},

			{
				request: "usr.CreateRecordRequest",
				handler: async (request, next) => {
					const handlerChain = sdk.HandlerChainService.instance;

					// Open a blank edit page with pre-filled default values
					await handlerChain.process({
						type: "crt.CreateRecordRequest",
						$context: request.$context,
						entityName: "Contact",
						defaultValues: [
							{ attributeName: "Name",  value: "New Contact" },
							{ attributeName: "Email", value: "example@mail.com" }
						]
					});

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
