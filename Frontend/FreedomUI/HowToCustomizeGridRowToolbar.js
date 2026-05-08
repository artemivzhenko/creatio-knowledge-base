define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to add custom actions to a grid row toolbar -----------------
		// When you add ANY item to rowToolbarItems, Creatio removes all defaults
		// (Open, Copy, Delete). You must re-declare them explicitly if you want
		// to keep them alongside your custom actions.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"name": "DataTable",
				"values": {
					"layoutConfig": {
						"basis": "100%",
						"width": 300
					},
					"columns": [
						{
							"id": "f252f581-0ccf-44ac-b7c9-c00df2ad9919",
							"code": "PDS_Name",
							"caption": "#ResourceString(PDS_Name)#",
							"dataValueType": 1
						}
					],
					"primaryColumnName": "PDS_Id",
					"sorting": "$ItemsSorting | crt.ToDataTableSortingConfig: 'Items'",
					"rowToolbarItems": [

						// Default actions - must be re-declared if rowToolbarItems is overridden

						{
							"type": "crt.MenuItem",
							"caption": "DataGrid.RowToolbar.Open",
							"icon": "edit-row-action",
							"disabled": "$Items.PrimaryModelMode | crt.IsEqual : 'create'",
							"clicked": {
								"request": "crt.UpdateRecordRequest",
								"params": {
									"itemsAttributeName": "Items",
									"recordId": "$Items.PDS_Id"
								}
							}
						},
						{
							"type": "crt.MenuItem",
							"caption": "DataGrid.RowToolbar.Copy",
							"icon": "copy-row-action",
							"disabled": "$Items.PrimaryModelMode | crt.IsEqual : 'create'",
							"clicked": {
								"request": "crt.CopyRecordRequest",
								"params": {
									"itemsAttributeName": "Items",
									"recordId": "$Items.PDS_Id"
								}
							}
						},
						{
							"type": "crt.MenuItem",
							"caption": "DataGrid.RowToolbar.Delete",
							"icon": "delete-row-action",
							"clicked": {
								"request": "crt.DeleteRecordRequest",
								"params": {
									"itemsAttributeName": "Items",
									"recordId": "$Items.PDS_Id"
								}
							}
						},

						// Custom actions

						// Run a business process for the selected record
						{
							"type": "crt.MenuItem",
							"caption": "Run process",
							"icon": "process-button-icon",
							"clicked": {
								"request": "crt.RunBusinessProcessRequest",
								"params": {
									"processName": "UsrMyProcess",
									"processRunType": "ForTheSelectedPage",
									"recordIdProcessParameterName": "ProcessRecordId"
								}
							}
						},

						// Custom handler - receives recordId via params.
						// "useRelativeContext": true passes the row's own context to the handler.
						{
							"type": "crt.MenuItem",
							"caption": "Do something",
							"icon": "open-button-icon",
							"clicked": {
								"request": "usr.RowActionRequest",
								"params": {
									"itemsAttributeName": "Items",
									"recordId": "$Items.PDS_Id"
								},
								"useRelativeContext": true
							}
						}

					]
				}
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.RowActionRequest",
				handler: async (request, next) => {
					const recordId = request.recordId;
					// use recordId to load or update the selected record
					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
