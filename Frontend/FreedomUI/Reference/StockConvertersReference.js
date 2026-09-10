define("MyPage_ListPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- Reference: stock converters and the pipe syntax -------------------
		// A binding string may pass its value through a chain of converters:
		//
		//   "$Attribute | converterName : arg1 : arg2 | anotherConverter"
		//
		//   |  separates the stages, left to right
		//   :  separates the arguments of one converter
		//   'literal'  single quotes for a string argument
		//   $Other     another attribute as an argument
		//
		// The chain is evaluated every time any referenced attribute changes.
		//
		// ===================== VALUE CONVERTERS ==============================
		//   crt.InvertBooleanValue   flips true/false - the usual way to drive
		//                            `readonly` from an "is editable" attribute
		//   crt.ToDisplayValue       lookup object -> its display string
		//   crt.ToDataTableSortingConfig  grid sorting config
		//
		// ===================== SELECTION AND COLLECTIONS =====================
		//   crt.ToCollectionFilters : '<gridName>' : $<gridName>_SelectionState
		//        turns the current grid selection into a filter set, so a request
		//        acts on exactly the selected rows
		//   crt.SkipIfSelectionEmpty : $<gridName>_SelectionState
		//        cancels the whole binding when nothing is selected - put it LAST
		//        so the request is not fired with an empty filter, which would
		//        otherwise mean "all rows"
		//   crt.ToValuesFromCollection  collection -> array of values
		//   crt.ToInFilter              array of values -> an IN filter
		//
		// ===================== FILTER ELEMENTS ===============================
		//   crt.SearchFilterAttributeConverter   binds a crt.SearchFilter to a
		//                                        data source filter attribute
		//   crt.QuickFilterAttributeConverter    same for crt.QuickFilter
		//
		// THE DANGEROUS ONE. A delete or a mass action bound to
		// crt.ToCollectionFilters WITHOUT crt.SkipIfSelectionEmpty will happily
		// run against the entire data source when the user has selected nothing.
		// Always chain the guard.
		//
		// Custom converters are declared in the `converters` section and used by
		// their key name - see HowToUseConverters.js.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Delete only the SELECTED rows, and do nothing when the selection
			// is empty.
			{
				"operation": "insert",
				"name": "DeleteSelectedButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(DeleteSelectedButton_caption)#",
					"clicked": {
						"request": "crt.DeleteRecordsRequest",
						"params": {
							"dataSourceName": "GridDetail_ouncw1lDS",
							"filters": "$GridDetail_ouncw1l | crt.ToCollectionFilters : 'GridDetail_ouncw1l' : $GridDetail_ouncw1l_SelectionState | crt.SkipIfSelectionEmpty : $GridDetail_ouncw1l_SelectionState"
						}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},

			// Tag the selected rows - the same selection chain.
			{
				"operation": "insert",
				"name": "AddTagsButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(AddTagsButton_caption)#",
					"clicked": {
						"request": "crt.AddTagsInRecordsRequest",
						"params": {
							"dataSourceName": "GridDetail_ouncw1lDS",
							"filters": "$GridDetail_ouncw1l | crt.ToCollectionFilters : 'GridDetail_ouncw1l' : $GridDetail_ouncw1l_SelectionState | crt.SkipIfSelectionEmpty : $GridDetail_ouncw1l_SelectionState"
						}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 1
			},

			// Invert a boolean to drive readonly.
			{
				"operation": "merge",
				"name": "NameInput",
				"values": {
					"readonly": "$IsEditable | crt.InvertBooleanValue"
				}
			},

			// Search filter wired to a data source filter attribute.
			{
				"operation": "insert",
				"name": "SearchFilter_main",
				"values": {
					"type": "crt.SearchFilter",
					"placeholder": "#ResourceString(SearchFilter_main_placeholder)#",
					"value": "$SearchFilter_main_value"
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 2
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					// The converter turns the search text into a data source filter.
					"SearchFilter_main_value": {
						"value": "",
						"converters": ["crt.SearchFilterAttributeConverter"]
					}
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
