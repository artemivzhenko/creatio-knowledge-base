// --- itemType and contentType reference --------------------------------------
// The designer emits these as bare numbers. Hand-written code should use the
// symbolic constants; both forms are shown below so generated schemas stay
// readable.
//
// itemType (Terrasoft.ViewItemType) - WHAT KIND of view element this is:
//
//   0   GRID_LAYOUT    a grid container that holds controls ("items": []).
//   1   TAB_PANEL      the tab panel itself.
//   2   DETAIL         an embedded detail; pair it with a `details` entry.
//                      Generated code marks these "markerValue": "added-detail".
//   3   MODEL_ITEM     a control bound to a column (text area, label block...).
//   4   CONTAINER      a plain container.
//   5   BUTTON         a button; needs caption + click.
//   15  CONTROL_GROUP  a collapsible field group with a caption.
//                      Generated code marks these "markerValue": "added-group".
//
// A plain field usually carries NO itemType at all - only bindTo + layout. The
// framework infers the control from the column type.
//
// contentType (Terrasoft.ContentType) - HOW a bound control renders:
//
//   0   TEXT       single-line text.
//   3   ENUM       lookup rendered as a dropdown list (small dictionaries).
//   4   RICH_TEXT  rich text editor (Notes-style fields).
//   5   LOOKUP     lookup rendered with a selection window (large dictionaries).
//
// Rule of thumb for lookups: ENUM (3) when the user should pick from a short
// dropdown, LOOKUP (5) when they need search and a "select" dialog.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		diff: /**SCHEMA_DIFF*/[
			{
				// Plain text column - no itemType, no contentType.
				"operation": "insert",
				"name": "QSName",
				"values": {
					"layout": { "colSpan": 12, "rowSpan": 1, "column": 0, "row": 0, "layoutName": "Header" },
					"bindTo": "QSName",
					"enabled": true
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 0
			},
			{
				// Lookup as a dropdown.
				"operation": "insert",
				"name": "QSTypeCargo",
				"values": {
					"layout": { "colSpan": 8, "rowSpan": 1, "column": 8, "row": 0, "layoutName": "Header" },
					"bindTo": "QSTypeCargo",
					"enabled": true,
					"contentType": 3   // Terrasoft.ContentType.ENUM
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 1
			},
			{
				// Lookup with a selection window.
				"operation": "insert",
				"name": "QSAccount",
				"values": {
					"layout": { "colSpan": 8, "rowSpan": 1, "column": 0, "row": 3, "layoutName": "Header" },
					"bindTo": "QSAccount",
					"enabled": true,
					"contentType": 5   // Terrasoft.ContentType.LOOKUP
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 2
			},
			{
				// Multiline / rich text.
				"operation": "insert",
				"name": "Notes",
				"values": {
					"bindTo": "QSNotes",
					"dataValueType": Terrasoft.DataValueType.TEXT,
					"contentType": Terrasoft.ContentType.RICH_TEXT,
					"layout": { "column": 0, "row": 0, "colSpan": 24, "rowSpan": 10 },
					"labelConfig": { "visible": false }
				},
				"parentName": "NotesControlGroup",
				"propertyName": "items",
				"index": 0
			},
			{
				// A tall text area declared as a model item.
				"operation": "insert",
				"name": "ShipmentInfoTextArea",
				"values": {
					"itemType": 3,   // Terrasoft.ViewItemType.MODEL_ITEM
					"layout": { "colSpan": 10, "rowSpan": 4, "column": 13, "row": 2, "layoutName": "MainGridLayout" },
					"bindTo": "QSShipmentInfoText",
					"contentType": 0
				},
				"parentName": "MainGridLayout",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_DIFF*/
	};
});
