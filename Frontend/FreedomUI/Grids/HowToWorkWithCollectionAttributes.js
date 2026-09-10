define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How a grid / detail is wired: collection attributes ---------------
		// A single-value field is one attribute. A GRID is a COLLECTION attribute
		// with a nested set of attributes, one per displayed column.
		//
		//   "GridDetail_3ywno5n": {
		//       "isCollection": true,
		//       "modelConfig": {
		//           "path": "GridDetail_3ywno5nDS",   // the data source
		//           "filterAttributes": []            // attributes that filter it
		//       },
		//       "viewModelConfig": {
		//           "attributes": {
		//               "GridDetail_3ywno5nDS_CreatedOn": {
		//                   "modelConfig": { "path": "GridDetail_3ywno5nDS.CreatedOn" }
		//               }
		//           }
		//       }
		//   }
		//
		// THE NAMING RULES, and they are strict:
		//   <Name>          the collection attribute, bound as "$<Name>" from the
		//                   grid element's `items`
		//   <Name>DS        the data source in modelConfigDiff
		//   <Name>DS_<Col>  one attribute per column; path "<Name>DS.<Col>"
		//   <Name>_SelectionState  the selection, used by the selection
		//                   converters (see StockConvertersReference.js)
		//
		// A column shown in the grid MUST have its attribute here, otherwise the
		// cell renders empty - the grid does not fetch columns on its own.
		// Include Id: the grid needs it as primaryColumnName.
		//
		// filterAttributes lists the attributes whose change reloads the
		// collection - this is how a search box or a quick filter is wired to a
		// grid without any handler code.
		//
		// A nested lookup column uses a dotted path:
		//   "path": "GridDetail_3ywno5nDS.QSAccount.Name"
		//
		// Reading a collection in a handler gives an array of plain objects keyed
		// by the ATTRIBUTE names, not by the column names.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "GridDetail_3ywno5n",
				"values": {
					"type": "crt.DataGrid",
					"items": "$GridDetail_3ywno5n",
					"primaryColumnName": "GridDetail_3ywno5nDS_Id",
					"visible": true,
					"fitContent": true
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {

					"GridDetail_3ywno5n": {
						"isCollection": true,
						"modelConfig": {
							"path": "GridDetail_3ywno5nDS",
							// Changing any of these reloads the collection.
							"filterAttributes": [
								{ "name": "SearchFilter_main_value", "loadOnChange": true }
							]
						},
						"viewModelConfig": {
							"attributes": {
								// One entry per column the grid shows.
								"GridDetail_3ywno5nDS_Id": {
									"modelConfig": { "path": "GridDetail_3ywno5nDS.Id" }
								},
								"GridDetail_3ywno5nDS_CreatedOn": {
									"modelConfig": { "path": "GridDetail_3ywno5nDS.CreatedOn" }
								},
								"GridDetail_3ywno5nDS_QSAppFLSendCurrency": {
									"modelConfig": { "path": "GridDetail_3ywno5nDS.QSAppFLSendCurrency" }
								},
								// A column reached through a lookup.
								"GridDetail_3ywno5nDS_QSAccountName": {
									"modelConfig": { "path": "GridDetail_3ywno5nDS.QSAccount.Name" }
								}
							}
						}
					}

				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["dataSources"],
				"values": {
					"GridDetail_3ywno5nDS": {
						"type": "crt.EntityDataSource",
						"config": { "entitySchemaName": "QSApplicationForFL" },
						"scope": "page"
					}
				}
			}
		]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.SumGridAmountsRequest",
				handler: async (request, next) => {
					// A collection attribute reads as an array of objects keyed
					// by the ATTRIBUTE names declared above.
					const rows = await request.$context.GridDetail_3ywno5n;

					const total = (rows || []).reduce(function(sum, row) {
						return sum + (row.GridDetail_3ywno5nDS_QSAppFLSendCurrency || 0);
					}, 0);

					request.$context.PDS_Total_x1y2z3 = total;
					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
