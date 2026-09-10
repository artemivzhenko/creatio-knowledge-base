// --- How to customise a section (SectionV2) and a mini page ------------------
// SECTION SCHEMA
//   properties.json -> "SchemaType": "ModuleViewModelSchema"
//   Naming: <Entity>SectionV2 for stock sections (AccountSectionV2), or the
//   designer-generated <Entity><8-hex>Section for custom ones.
//   A section schema is a Classic UI view model with entitySchemaName, details,
//   diff and methods - the same API as a page, applied to the list view.
//
//   Typical section work:
//     - remove a stock command, e.g. the add button of the separate mode:
//         { "operation": "remove", "name": "SeparateModeAddRecordButton" }
//     - add a section button into "ActionButtonsContainer" or the command bar
//     - override getFilters / initFixedFiltersConfig to preset list filters
//     - override getEditPageName to route to different edit pages by record type
//
//   Note on this codebase: the section schemas in the QubeSoft package are
//   nearly empty - they only carry entitySchemaName and small diff removals.
//   The pattern below reflects that shape.
//
// MINI PAGE
//   properties.json -> "SchemaType": "EditViewModelSchema" (same as a page).
//   Naming: <Entity>MiniPage.
//   Layout differences from a full page:
//     - the root container is "MiniPage", not "Header"
//     - every inserted control needs "layoutName": "MiniPage" and
//       "isMiniPageModelItem": true
//     - the grid is still 24 columns, but a mini page is one column wide in
//       practice, so controls use "colSpan": 24
//   "visible": { "bindTo": "isAddMode" } is the usual way to show a field only
//   while the record is being created from the mini page.

// ============================ SECTION SCHEMA =================================
define("QSMyEntitySection", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,
		diff: /**SCHEMA_DIFF*/[
			{
				// Drop the stock add button of the separate (full-screen) mode.
				"operation": "remove",
				"name": "SeparateModeAddRecordButton"
			}
		]/**SCHEMA_DIFF*/,
		methods: {}
	};
});

// ============================= MINI PAGE =====================================
// define("QSMyEntityMiniPage", [], function() {
//     return {
//         entitySchemaName: "QSMyEntity",
//         attributes: {},
//         details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,
//         businessRules: /**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/,
//         methods: {},
//         diff: /**SCHEMA_DIFF*/[
//             {
//                 // Re-layout an inherited control.
//                 "operation": "merge",
//                 "name": "HeaderContainer",
//                 "values": {
//                     "layout": { "colSpan": 24, "rowSpan": 1, "column": 0, "row": 0 }
//                 }
//             },
//             {
//                 // Add a field: note layoutName, isMiniPageModelItem and parentName.
//                 "operation": "insert",
//                 "name": "Industry931db2ec-97b3-4f4d-9074-ff8b1ab69a00",
//                 "values": {
//                     "layout": { "colSpan": 24, "rowSpan": 1, "column": 0, "row": 3,
//                                 "layoutName": "MiniPage" },
//                     "isMiniPageModelItem": true,
//                     "bindTo": "Industry",
//                     // Only while creating a record from the mini page.
//                     "visible": { "bindTo": "isAddMode" }
//                 },
//                 "parentName": "MiniPage",
//                 "propertyName": "items",
//                 "index": 2
//             }
//         ]/**SCHEMA_DIFF*/
//     };
// });
