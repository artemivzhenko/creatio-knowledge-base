define("MyPage_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		// --- Reference: sdk filters, enums and services ------------------------
		// Everything here comes from "@creatio-devkit/common", so the schema must
		// declare that dependency and take the `sdk` argument.
		//
		// ===================== FILTERS =======================================
		//   const filter = new sdk.FilterGroup();
		//   filter.logicalOperation = sdk.LogicalOperatorType.Or;   // default: And
		//   await filter.addSchemaColumnFilterWithParameter(
		//       sdk.ComparisonType.Equal, "ColumnPath", value);
		//
		// The constructor also accepts the operator directly:
		//   new sdk.FilterGroup(sdk.LogicalOperatorType.And)
		//
		// addSchemaColumnFilterWithParameter is ASYNCHRONOUS - await it, or the
		// filter may be handed to the query before it is built.
		//
		// ===================== sdk.ComparisonType ============================
		// The devkit enum uses "Word" or "Word_word" casing, NOT the SCREAMING
		// CASE of the Classic UI Terrasoft.ComparisonType:
		//
		//   sdk.ComparisonType.Equal
		//   sdk.ComparisonType.Not_equal
		//   sdk.ComparisonType.Contain
		//   sdk.ComparisonType.Greater_or_equal
		//   sdk.ComparisonType.Less_or_equal
		//
		// CAUTION - two spellings are mixed in this repository. The dominant and
		// documented form is the one above; a few files use "NotEqual" and
		// "LogicalOperatorType.AND"/".OR", which look like the Classic UI enum.
		// An enum member that does not exist evaluates to `undefined` and the
		// filter is built with an undefined comparison, which usually degrades
		// silently rather than throwing. Verify against the SDK typings before
		// copying either form; do not assume both work.
		//
		// ===================== sdk.LogicalOperatorType =======================
		//   sdk.LogicalOperatorType.And
		//   sdk.LogicalOperatorType.Or
		//
		// ===================== sdk.ModelParameterType ========================
		//   sdk.ModelParameterType.Filter              a FilterGroup
		//   sdk.ModelParameterType.PrimaryColumnValue  read one record by id
		//   sdk.ModelParameterType.ColumnValue         a single column value
		//
		// ===================== SERVICES ======================================
		//   sdk.Model.create("<EntityName>")     load / insert / update records
		//                                        (see HowToLoadDataWithSdkModel.js)
		//   sdk.HandlerChainService.instance     .process({ type, $context, ... })
		//                                        run a request through the chain
		//   sdk.DialogService                    .open({ message, actions })
		//                                        (see HowToShowDialog.js)
		//   sdk.RightsService                    .getCanExecuteOperation(code)
		//                                        (see HowToCheckAccessRights.js)
		//   sdk.request.send(type, config)       send a request directly
		//
		// EXECUTING A REQUEST - three equivalent routes, pick by context:
		//   request.$context.executeRequest({ type, $context, ... })  most common
		//   sdk.HandlerChainService.instance.process({ type, $context, ... })
		//   sdk.request.send(type, { $context, ... })

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[

			// A simple AND filter, read through sdk.Model.
			{
				request: "usr.LoadApplicationRequest",
				handler: async (request, next) => {
					const flAppId = await request.$context.PDS_ApplicationId_a1b2c3d;

					const model = await sdk.Model.create("QSApplicationForFL");
					const records = await model.load({
						attributes: ["QSAnySender", "QSOptionToSendFunds", "QSPayer"],
						parameters: [{
							type: sdk.ModelParameterType.Filter,
							value: (new sdk.FilterGroup()).addSchemaColumnFilterWithParameter(
								sdk.ComparisonType.Equal, "Id", flAppId)
						}]
					});

					if (records.length > 0) {
						request.$context.PDS_Payer_b2c3d4e = records[0].QSPayer;
					}
					return next?.handle(request);
				}
			},

			// An OR group built in a loop.
			{
				request: "usr.FilterByCardsRequest",
				handler: async (request, next) => {
					const cards = await request.$context.SelectedCards;

					const filter = new sdk.FilterGroup();
					filter.logicalOperation = sdk.LogicalOperatorType.Or;

					for (const card of cards) {
						if (card.UsrDoctor?.value) {
							await filter.addSchemaColumnFilterWithParameter(
								sdk.ComparisonType.Equal, "Id", card.UsrDoctor.value);
						}
					}

					request.$context.DoctorFilter = filter;
					return next?.handle(request);
				}
			},

			// Reading a single record by its primary key.
			{
				request: "usr.LoadOneRecordRequest",
				handler: async (request, next) => {
					const model = await sdk.Model.create("QSOrder");
					const records = await model.load({
						attributes: ["QSName", "QSStatus"],
						parameters: [{
							type: sdk.ModelParameterType.PrimaryColumnValue,
							value: await request.$context.PDS_OrderId_c3d4e5f
						}]
					});
					console.log(records[0]?.QSName);
					return next?.handle(request);
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
