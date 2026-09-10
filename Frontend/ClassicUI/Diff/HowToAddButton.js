// --- How to add a button to a page -------------------------------------------
// A button is a diff entry with itemType 5 (Terrasoft.ViewItemType.BUTTON):
//
//   caption  - bind to a resource string, never a literal.
//   click    - bind to a method name in `methods`; it is called with no args.
//   enabled  - bind to a virtual boolean attribute to control availability.
//   visible  - bind to a virtual boolean or to a base method such as isAddMode.
//   style    - "green", "blue", "red", "default", or use
//              Terrasoft.controls.ButtonEnums.style.* (TRANSPARENT, BLUE, GREEN).
//   markerValue - stable marker used by autotests; set it for testable buttons.
//
// Where to put it:
//   parentName "Header"        - the page header block.
//   parentName "ActionButtonsContainer"
//   parentName "LeftContainer" / "RightContainer" - the top command bar.
//   parentName "<TabName>GridLayout<suffix>"      - inside a tab.
//
// If the button needs a saved record, check this.get("Id") first and tell the
// user to save instead of failing silently.

define("QSMyEntity1Page", ["ProcessModuleUtilities"], function(ProcessModuleUtilities) {
	return {
		entitySchemaName: "QSMyEntity",
		attributes: {
			"CreateFreightKPButtonEnabled": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN,
				"value": false
			}
		},
		methods: {

			onCreateComplexKPButtonClick: function() {
				var recordId = this.get("Id");
				if (!recordId) {
					this.showInformationDialog(this.get("Resources.Strings.SaveRecordFirstMessage"));
					return;
				}
				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_2da82f9",
					parameters: { orderId: recordId }
				});
			},

			onCreateFreightKPButtonClick: function() {
				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_2da82f9_52b58f7",
					parameters: { orderId: this.get("Id") }
				});
			}
		},
		diff: /**SCHEMA_DIFF*/[
			{
				"operation": "insert",
				"name": "CreateComplexKPButton",
				"values": {
					"itemType": 5,
					"layout": { "colSpan": 6, "rowSpan": 1, "column": 17, "row": 10, "layoutName": "Header" },
					"caption": { "bindTo": "Resources.Strings.CreateComplexKPButtonCaption" },
					"click":   { "bindTo": "onCreateComplexKPButtonClick" },
					"style":   "green"
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 26
			},
			{
				// Same button, availability driven by page logic.
				"operation": "insert",
				"name": "CreateFreightKPButton",
				"values": {
					"itemType": 5,
					"layout": { "colSpan": 6, "rowSpan": 1, "column": 17, "row": 13, "layoutName": "Header" },
					"caption": { "bindTo": "Resources.Strings.CreateFreightKPButtonCaption" },
					"click":   { "bindTo": "onCreateFreightKPButtonClick" },
					"enabled": { "bindTo": "CreateFreightKPButtonEnabled" },
					"markerValue": "create-freight-kp",
					"style":   "green"
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 33
			}
		]/**SCHEMA_DIFF*/
	};
});
