define("UsrMyCustomEntity_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to dynamically filter a lookup field ------------------------
		// Handle crt.LoadDataRequest and check request.dataSourceName to target
		// a specific lookup's DataSource. Push a filter into request.parameters
		// before passing the request to the next handler.
		//
		// dataSourceName - find it in the page schema; it is the attribute name
		//   of the lookup with "_DS" appended (e.g. "MyLookupField_List_DS").
		//
		// The filter must be added as { type: "filter", value: filterGroup }.
		// Use Object.assign to copy the FilterGroup so the structure is preserved.
		//
		// Requires: @creatio-devkit/common in SCHEMA_DEPS (sdk argument).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.LoadDataRequest",
				handler: async (request, next) => {
					if (request.dataSourceName === "Field_Name_List_DS") {
						const guidValue = await request.$context.PDS_RelatedField_someAttr;

						const filter = new sdk.FilterGroup();
						await filter.addSchemaColumnFilterWithParameter(
							sdk.ComparisonType.Equal,
							"RelatedColumn",
							guidValue
						);

						// Object.assign preserves the FilterGroup structure
						const newFilter = Object.assign({}, filter);
						newFilter.items = filter.items;

						request.parameters.push({
							type: "filter",
							value: newFilter
						});
					}

					return await next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
