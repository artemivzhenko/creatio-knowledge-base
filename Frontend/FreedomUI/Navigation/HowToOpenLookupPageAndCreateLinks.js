define("MyPage_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		// --- How to open a record picker and create link records --------------
		// crt.OpenLookupPageRequest opens the modal record-selection window. It
		// is the Freedom UI answer to "let the user pick several records and add
		// them to a detail".
		//
		//   type              "crt.OpenLookupPageRequest"
		//   $context          always request.$context
		//   entitySchemaName  the entity to pick from
		//   features          what the window allows:
		//       select { multiple, selectAll, resultType }
		//           multiple    true -> checkboxes
		//           selectAll   true -> "select all" control
		//           resultType  "lookupValues" gives { value, displayValue }
		//                       items back
		//       create { enabled }  show the "new record" action
		//   filtersConfig     restricts what the window shows:
		//       filterAttributes  [{ name, loadOnChange }]
		//       attributesConfig  { <name>: { value: <sdk.FilterGroup> } }
		//   afterClosed       async callback receiving the selected items;
		//                     it is NOT called with a cancel, and the array can
		//                     still be empty - guard for both
		//
		// CREATING THE LINK ROWS. The window only returns a selection; writing
		// the link records is your job. sdk.Model.create("<LinkEntity>") plus
		// model.insert({...}) per item is the pattern used in this repository.
		//
		// Inserting in a loop issues one request per row. That is fine for a
		// handful of records and slow for dozens - for large selections push the
		// list into a business process instead.
		//
		// The master record must already exist: a link row needs its id. On a
		// page that may still be new, save first (crt.SaveRecordRequest) or read
		// the id and bail out with a message when it is empty.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "AddCarsButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(AddCarsButton_caption)#",
					"iconPosition": "only-text",
					"clicked": { "request": "usr.AddCarsRequest", "params": {} }
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.AddCarsRequest",
				handler: async (request, next) => {

					const applicationId = await request.$context.PDS_Id_a1b2c3d;
					if (!applicationId) {
						// No master record yet - nothing to link to.
						return next?.handle(request);
					}

					// Optional: narrow the picker with a filter group.
					const customFilter = new sdk.FilterGroup();
					await customFilter.addSchemaColumnFilterWithParameter(
						sdk.ComparisonType.Equal, "SuIsActive", true);

					await request.$context.executeRequest({
						type: "crt.OpenLookupPageRequest",
						$context: request.$context,
						entitySchemaName: "SuSaleProductCar",

						features: {
							select: {
								multiple: true,
								selectAll: false,
								resultType: "lookupValues"
							},
							create: {
								enabled: true
							}
						},

						filtersConfig: {
							filterAttributes: [
								{ name: "CustomFilter", loadOnChange: false }
							],
							attributesConfig: {
								CustomFilter: { value: customFilter }
							}
						},

						afterClosed: async function(selectedItems) {
							// Cancel or empty selection.
							if (!selectedItems?.length) {
								return;
							}

							// Create one link record per selected item.
							const model = await sdk.Model.create("SuCarInSaleProduct");
							for (const item of selectedItems) {
								await model.insert({
									SuSaleProductCar: item.value,
									SuSaleProductApplication: applicationId
								});
							}

							// Refresh the detail that shows the link records.
							await request.$context.executeRequest({
								type: "crt.LoadDataRequest",
								$context: request.$context,
								dataSourceName: "GridDetail_carsDS"
							});
						}
					});

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
