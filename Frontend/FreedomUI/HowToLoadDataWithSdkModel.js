define("UsrEntity_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to load records from an entity using sdk.Model --------------
		// Use sdk.Model when you need to query any entity with custom filters
		// from inside a handler, without declaring a DataSource in modelConfigDiff.
		//
		// sdk.Model.create("SchemaName") - initializes access to the entity.
		// sdk.FilterGroup              - builds one or more filter conditions.
		// addSchemaColumnFilterWithParameter(type, column, value) - adds a filter.
		// load({ attributes, parameters }) - executes the query and returns records.
		//
		// Requires: @creatio-devkit/common in SCHEMA_DEPS (sdk argument).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					await next?.handle(request);

					const typeId  = await request.$context.PDS_Type_someAttr;
					const thisId  = await request.$context.PDS_Id_someAttr;

					// Initialize model for the target entity
					const model = await sdk.Model.create("Contact");

					// Build a filter group
					const filters = new sdk.FilterGroup();
					await filters.addSchemaColumnFilterWithParameter(
						sdk.ComparisonType.Equal,
						"Type",
						typeId
					);

					// Load records - specify only the columns you need
					const records = await model.load({
						attributes: ["Id", "Name"],
						parameters: [{
							type: sdk.ModelParameterType.Filter,
							value: filters
						}]
					});

					records.forEach(item => {
						if (item.Id !== thisId) {
							console.log(item.Id, item.Name);
						}
					});
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
