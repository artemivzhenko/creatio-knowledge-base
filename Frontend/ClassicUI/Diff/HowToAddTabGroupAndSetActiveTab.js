// --- How to add a tab, a field group, and switch the active tab --------------
// STRUCTURE of a Classic UI page body:
//
//   Tabs                      (the tab panel)
//     └─ <TabName>            a tab; inserted into parentName "Tabs",
//                             propertyName "tabs"
//          └─ <GroupName>     itemType 15 (CONTROL_GROUP), has a caption
//               └─ <LayoutName>  itemType 0 (GRID_LAYOUT), "items": []
//                    └─ fields, buttons, details
//
// You need all three levels. Dropping the grid layout and putting fields
// straight into the group breaks the 24-column layout.
//
// Naming: the designer generates names like "Tab745c99d0TabLabel" and
// "Tab745c99d0TabLabelGroup2cd602df". Hand-written schemas may use readable
// names, but they must stay unique across the whole inheritance chain.
//
// SWITCHING TABS from code: this.setActiveTab("<TabName>"). Call it from
// onEntityInitialized, when the entity data is available. Well-known stock tab
// names: "NotesAndFilesTab", "ESNTab".

define("QSMyEntity1Page", [], function() {

	const NoticeTypeArrival = "475d7b08-33e0-4f91-b219-bb8a78ec2f85";

	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			onEntityInitialized: function() {
				this.callParent(arguments);

				// Open the page on a specific tab depending on the record.
				var noticeType = this.get("QSNoticeType");
				if (noticeType && noticeType.value === NoticeTypeArrival) {
					this.setActiveTab("NotesAndFilesTab");
				} else {
					this.setActiveTab("QSLogisticsTab");
				}
			}
		},
		diff: /**SCHEMA_DIFF*/[
			{
				// 1. The tab itself.
				"operation": "insert",
				"name": "QSLogisticsTab",
				"values": {
					"caption": { "bindTo": "Resources.Strings.QSLogisticsTabCaption" },
					"items": [],
					"order": 2
				},
				"parentName": "Tabs",
				"propertyName": "tabs",
				"index": 2
			},
			{
				// 2. A field group inside the tab.
				"operation": "insert",
				"name": "QSLogisticsTabMainGroup",
				"values": {
					"caption": { "bindTo": "Resources.Strings.QSLogisticsTabMainGroupCaption" },
					"itemType": 15,               // CONTROL_GROUP
					"markerValue": "added-group",
					"items": []
				},
				"parentName": "QSLogisticsTab",
				"propertyName": "items",
				"index": 0
			},
			{
				// 3. The grid layout inside the group.
				"operation": "insert",
				"name": "QSLogisticsTabMainGridLayout",
				"values": {
					"itemType": 0,                // GRID_LAYOUT
					"items": []
				},
				"parentName": "QSLogisticsTabMainGroup",
				"propertyName": "items",
				"index": 0
			},
			{
				// 4. A field inside the grid layout.
				"operation": "insert",
				"name": "QSCarrier",
				"values": {
					"layout": { "colSpan": 12, "rowSpan": 1, "column": 0, "row": 0,
						"layoutName": "QSLogisticsTabMainGridLayout" },
					"bindTo": "QSCarrier",
					"enabled": true,
					"contentType": 5
				},
				"parentName": "QSLogisticsTabMainGridLayout",
				"propertyName": "items",
				"index": 0
			},
			{
				// Reorder an inherited tab.
				"operation": "move",
				"name": "ESNTab",
				"parentName": "Tabs",
				"propertyName": "tabs",
				"index": 0
			}
		]/**SCHEMA_DIFF*/
	};
});
