define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "ActionButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Run",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.DemoRequest",
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

		// --- How to read and set field values via request.$context -----------
		//
		// All attribute reads are async - use await.
		// Lookup fields return { value: guid, displayValue: string }.
		// Grid detail attributes live on request.$context.attributes, not directly
		// on $context, and contain a keyed object where numeric keys are row indexes.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.DemoRequest",
				handler: async (request, next) => {

					// Read a plain field
					const id = await request.$context.Id;

					// Read a lookup field
					const type = await request.$context.Type;
					if (type.displayValue === "Customer") {
						// handle customer-specific logic
					}

					// Read a grid detail.
					// Grid detail attributes sit on request.$context.attributes.
					// Rows are stored under numeric string keys ("0", "1", ...).
					const gridDetail = await request.$context.attributes.GridDetail_1ky8t6m;

					let totalDuration = 0;
					for (const key of Object.keys(gridDetail)) {
						if (!isNaN(Number(key))) {
							totalDuration += gridDetail[key]["attributes"]["GridDetail_1ky8t6mDS_Duration"];
						}
					}

					// Set a plain field
					request.$context.FieldName = "New value";

					// Set a lookup field - always pass both value (Guid) and displayValue (string)
					request.$context.Type = {
						value: "someGuid",
						displayValue: "Customer"
					};

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
