// --- How to build a new Classic UI page from scratch -------------------------
// Checklist for a custom page over your own entity:
//
//   1. Create the Entity (object) first - the page binds to it by name.
//   2. Create a client schema of type EditViewModelSchema, parent
//      BasePageV2 (or the stock page you are extending).
//      properties.json -> "SchemaType": "EditViewModelSchema"
//   3. Set entitySchemaName to your entity.
//   4. Add controls to the header through diff, parentName "ProfileContainer"
//      (left profile block) or "Header" (the main header grid).
//   5. Add tabs into parentName "Tabs", propertyName "tabs".
//   6. Register details in `details` and render them with an itemType DETAIL
//      insert (see Details/HowToAddDetailToPage.js).
//   7. Put every caption into the schema resources
//      (see HowToUseLocalizableStrings.js).
//   8. Register the section / page in a workplace so users can reach it.
//
// WELL-KNOWN CONTAINER NAMES on a Classic UI page:
//   "ProfileContainer"     left profile block of the header
//   "Header"               main header grid layout
//   "Tabs"                 the tab panel (propertyName "tabs")
//   "NotesAndFilesTab"     the stock notes and attachments tab
//   "ActionButtonsContainer", "LeftContainer", "RightContainer" - command bar
//
// ATTACHMENTS. Reuse the stock detail rather than writing one: schemaName
// "FileDetailV2" over your <Entity>File table. The key in `details` is the name
// you reference from diff.
//
// NOTES FIELD. Insert a control bound to your notes column with
// contentType RICH_TEXT and labelConfig.visible false, into the same tab.

define("QSLogistWorkplace1Page", [], function() {
	return {
		entitySchemaName: "QSLogistWorkplace",
		attributes: {},
		modules: /**SCHEMA_MODULES*/{}/**SCHEMA_MODULES*/,

		details: /**SCHEMA_DETAILS*/{
			// Stock attachments detail over the entity file table.
			"Files": {
				"schemaName": "FileDetailV2",
				"entitySchemaName": "QSLogistWorkplaceFile",
				"filter": {
					"masterColumn": "Id",
					"detailColumn": "QSLogistWorkplace"
				}
			}
		}/**SCHEMA_DETAILS*/,

		businessRules: /**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/,
		methods: {},

		diff: /**SCHEMA_DIFF*/[
			{
				// Title field in the profile block.
				"operation": "insert",
				"name": "QSName",
				"values": {
					"layout": { "colSpan": 24, "rowSpan": 1, "column": 0, "row": 0,
						"layoutName": "ProfileContainer" },
					"bindTo": "QSName"
				},
				"parentName": "ProfileContainer",
				"propertyName": "items",
				"index": 0
			},
			{
				// Notes and attachments tab.
				"operation": "insert",
				"parentName": "Tabs",
				"propertyName": "tabs",
				"index": 0,
				"name": "NotesAndFilesTab",
				"values": {
					"caption": { "bindTo": "Resources.Strings.NotesAndFilesTabCaption" },
					"items": []
				}
			},
			{
				// Attachments detail inside that tab. The name matches the
				// `details` key above.
				"operation": "insert",
				"parentName": "NotesAndFilesTab",
				"propertyName": "items",
				"name": "Files",
				"values": {
					"itemType": Terrasoft.ViewItemType.DETAIL
				}
			},
			{
				// A group to hold the notes control.
				"operation": "insert",
				"parentName": "NotesAndFilesTab",
				"propertyName": "items",
				"name": "NotesControlGroup",
				"values": {
					"itemType": Terrasoft.ViewItemType.CONTROL_GROUP,
					"caption": { "bindTo": "Resources.Strings.NotesGroupCaption" },
					"items": []
				}
			},
			{
				// Rich text notes filling the group.
				"operation": "insert",
				"parentName": "NotesControlGroup",
				"propertyName": "items",
				"name": "Notes",
				"values": {
					"bindTo": "QSNotes",
					"dataValueType": Terrasoft.DataValueType.TEXT,
					"contentType": Terrasoft.ContentType.RICH_TEXT,
					"layout": { "column": 0, "row": 0, "colSpan": 24, "rowSpan": 10 },
					"labelConfig": { "visible": false }
				}
			}
		]/**SCHEMA_DIFF*/
	};
});
