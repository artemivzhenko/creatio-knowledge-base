define("MyPage_ListPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to export, import, delete and tag list records ----------------
		// Four stock requests cover the bulk actions of a list. All of them are
		// wired declaratively from a button - no handler code is needed.
		//
		//   crt.ExportDataGridToExcelRequest
		//       params { viewName: "<grid element name>" }
		//       Exports what the grid currently shows, including its filters and
		//       column set. Note it takes viewName - the VIEW ELEMENT name - not
		//       a data source name.
		//
		//   crt.ImportDataRequest
		//       Opens the data import wizard. Usually no params.
		//
		//   crt.DeleteRecordsRequest
		//       params { dataSourceName, filters }
		//       Takes a DATA SOURCE name, not a view name. `filters` decides what
		//       is deleted - build it from the selection, always with the
		//       empty-selection guard (below).
		//
		//   crt.AddTagsInRecordsRequest / crt.RemoveTagsInRecordsRequest
		//       Same shape as delete: dataSourceName plus selection filters.
		//
		// THE SELECTION CHAIN, used by delete and both tag requests:
		//
		//   "$<Grid> | crt.ToCollectionFilters : '<Grid>' : $<Grid>_SelectionState
		//            | crt.SkipIfSelectionEmpty : $<Grid>_SelectionState"
		//
		// Drop crt.SkipIfSelectionEmpty and an empty selection produces an empty
		// filter, which means "every row in the data source". On a delete button
		// that is a data-loss bug, and it is silent. See
		// StockConvertersReference.js.
		//
		// Note the asymmetry, it is a common source of mistakes: export takes
		// viewName, delete and tagging take dataSourceName.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Export the grid as it is displayed.
			{
				"operation": "insert",
				"name": "ExportToExcelButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(ExportToExcelButton_caption)#",
					"iconPosition": "only-text",
					"clicked": {
						"request": "crt.ExportDataGridToExcelRequest",
						"params": { "viewName": "GridDetail_jyzmfof" }
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},

			// Open the import wizard.
			{
				"operation": "insert",
				"name": "ImportDataButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(ImportDataButton_caption)#",
					"clicked": {
						"request": "crt.ImportDataRequest",
						"params": {}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 1
			},

			// Delete only the selected rows.
			{
				"operation": "insert",
				"name": "DeleteSelectedButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(DeleteSelectedButton_caption)#",
					"clicked": {
						"request": "crt.DeleteRecordsRequest",
						"params": {
							"dataSourceName": "GridDetail_jyzmfofDS",
							"filters": "$GridDetail_jyzmfof | crt.ToCollectionFilters : 'GridDetail_jyzmfof' : $GridDetail_jyzmfof_SelectionState | crt.SkipIfSelectionEmpty : $GridDetail_jyzmfof_SelectionState"
						}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 2
			},

			// Tag / untag the selected rows.
			{
				"operation": "insert",
				"name": "AddTagsButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(AddTagsButton_caption)#",
					"clicked": {
						"request": "crt.AddTagsInRecordsRequest",
						"params": {
							"dataSourceName": "GridDetail_jyzmfofDS",
							"filters": "$GridDetail_jyzmfof | crt.ToCollectionFilters : 'GridDetail_jyzmfof' : $GridDetail_jyzmfof_SelectionState | crt.SkipIfSelectionEmpty : $GridDetail_jyzmfof_SelectionState"
						}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 3
			},
			{
				"operation": "insert",
				"name": "RemoveTagsButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(RemoveTagsButton_caption)#",
					"clicked": {
						"request": "crt.RemoveTagsInRecordsRequest",
						"params": {
							"dataSourceName": "GridDetail_jyzmfofDS",
							"filters": "$GridDetail_jyzmfof | crt.ToCollectionFilters : 'GridDetail_jyzmfof' : $GridDetail_jyzmfof_SelectionState | crt.SkipIfSelectionEmpty : $GridDetail_jyzmfof_SelectionState"
						}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 4
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
