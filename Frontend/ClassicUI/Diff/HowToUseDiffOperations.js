// --- How the diff array works ------------------------------------------------
// `diff` is a list of declarative modifications applied to the view produced by
// the PARENT schema. Every entry has:
//
//   operation   - "insert" | "merge" | "remove" | "move"
//   name        - unique name of the view element being touched
//   values      - element configuration (insert / merge only)
//   parentName  - name of the container that owns the element (insert / move)
//   propertyName- collection on the parent: usually "items", "tabs" for tabs
//   index       - position inside that collection (insert / move)
//
// Operations:
//
//   insert - add a NEW element. Requires name, values, parentName, propertyName.
//            `index` decides the order among siblings.
//   merge  - patch an EXISTING element (inherited or inserted earlier). Only the
//            keys you list are overwritten; everything else is kept. This is how
//            you re-layout, rename, hide or re-bind a stock field.
//   remove - delete an existing element. Only `name` is needed.
//   move   - relocate an existing element to another parent / index.
//
// Order matters: entries are applied top to bottom, so you can insert an element
// and merge it later in the same array.
//
// LAYOUT. Controls live in a 24-column grid:
//   "layout": { "column": 0, "row": 3, "colSpan": 12, "rowSpan": 1,
//               "layoutName": "Header" }
//   column   0..23     starting column
//   colSpan  1..24     width; 12 = half width, 24 = full width
//   row                zero-based row inside the layout
//   rowSpan            height in rows (text areas use 3-4)
//   layoutName         the grid layout the control belongs to; "Header" is the
//                      page header block, tabs use their generated layout name.
//
// Rows are NOT auto-packed. Two controls with the same column/row overlap, and a
// gap in `row` renders as empty space. When inserting into a stock page, read the
// existing layout first and pick free coordinates.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		diff: /**SCHEMA_DIFF*/[
			{
				// INSERT: a new field in the page header.
				"operation": "insert",
				"name": "QSDeliveryDate",
				"values": {
					"layout": { "colSpan": 8, "rowSpan": 1, "column": 0, "row": 4, "layoutName": "Header" },
					"bindTo": "QSDeliveryDate",
					"enabled": true
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 12
			},
			{
				// MERGE: re-layout and disable an inherited field. Everything not
				// listed here (caption, tip, validation) is preserved.
				"operation": "merge",
				"name": "AlternativeName",
				"values": {
					"layout": { "colSpan": 12, "rowSpan": 1, "column": 0, "row": 0 },
					"enabled": false
				}
			},
			{
				// MERGE with a binding instead of a constant.
				"operation": "merge",
				"name": "QSFactDateUnloading",
				"values": {
					"enabled": { "bindTo": "QSFactDateUnloadingEnabled" }
				}
			},
			{
				// REMOVE: drop an inherited element entirely.
				"operation": "remove",
				"name": "SeparateModeAddRecordButton"
			},
			{
				// MOVE: put an inherited tab first.
				"operation": "move",
				"name": "ESNTab",
				"parentName": "Tabs",
				"propertyName": "tabs",
				"index": 0
			},
			{
				// MERGE on a container only to change its display order.
				"operation": "merge",
				"name": "AccountPageGeneralTabContainer",
				"values": { "order": 1 }
			}
		]/**SCHEMA_DIFF*/
	};
});
