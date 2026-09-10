// --- How to customise section modes, buttons and behaviour -------------------
// SOURCE: _SalesUp_DT_ITSM/Schemas/BaseLookupSection - a real section schema
// (SchemaType "ModuleViewModelSchema") that replaces the stock lookup section.
//
// A Classic UI section renders in two MODES and each has its own command
// containers, so a button added to one mode is invisible in the other:
//
//   COMBINED mode  - the list plus the preview area (the default view)
//       "CombinedModeAddRecordButton"
//       "CombinedModeActionButtonsCotainer"   (note the stock typo)
//   SEPARATE mode  - the full-screen list
//       "SeparateModeAddRecordButton"
//       "SeparateModeActionButtonsLeftContainer"
//       "SeparateModeActionButtonsRightContainer"
//
// To swap the stock "add" button for your own you must hide BOTH mode variants
// and insert your button into the container of the mode you support.
//
// A REPLACING SECTION serves every entity that inherits the base section, so
// guard your customisation with entitySchemaName - the same schema is loaded
// for lookups you did not mean to change.
//
// DEPENDENCIES worth noting:
//   "<SchemaName>Resources"      - gives the factory the schema resources
//                                  argument; needed when the module reads
//                                  resources outside the view model.
//   "StructureExplorerUtilities" - see Fields/HowToOpenStructureExplorer.js
//
// Section-level data methods: this.reloadGridData() re-reads the list after you
// write records directly with an InsertQuery.

define("BaseLookupSection", ["BaseLookupSectionResources", "StructureExplorerUtilities"],
	function(resources) {

		const TARGET_SCHEMA_NAME = "SuChangeLogCaseSetting";

		return {
			methods: {

				init: function() {
					this.callParent(arguments);
					try {
						// The same replacing schema serves every lookup section:
						// switch the custom UI on only for the target entity.
						const isTargetLookup = this.entitySchemaName === TARGET_SCHEMA_NAME;
						this.set("SuAddColumnsButtonVisible", isTargetLookup);
						this.set("SuBaseAddButtonVisible", !isTargetLookup);
					} catch (e) {
						console.error("BaseLookupSection: init failed.", e);
					}
				},

				onSuAddColumnsClick: function() {
					this.openColumnExplorer();
				},

				openColumnExplorer: function() {},

				// After writing rows directly, refresh the list.
				insertColumn: function(columnName, columnCaption) {
					const insert = Ext.create("Terrasoft.InsertQuery", {
						rootSchemaName: TARGET_SCHEMA_NAME
					});
					insert.setParameterValue("Name", columnCaption, Terrasoft.DataValueType.TEXT);
					insert.execute(function() {
						this.reloadGridData();
					}, this);
				}
			},

			diff: /**SCHEMA_DIFF*/[
				{
					// Custom button in the separate-mode command bar.
					"operation": "insert",
					"name": "SuAddColumnsButton",
					"parentName": "SeparateModeActionButtonsLeftContainer",
					"propertyName": "items",
					"values": {
						"itemType": Terrasoft.ViewItemType.BUTTON,
						"caption": { "bindTo": "Resources.Strings.SuAddColumnsButtonCaption" },
						"style": Terrasoft.controls.ButtonEnums.style.GREEN,
						"click": { "bindTo": "onSuAddColumnsClick" },
						"visible": { "bindTo": "SuAddColumnsButtonVisible" }
					},
					"index": 0
				},
				{
					// Hide the stock add button - separate mode.
					"operation": "merge",
					"name": "SeparateModeAddRecordButton",
					"values": {
						"visible": { "bindTo": "SuBaseAddButtonVisible" }
					}
				},
				{
					// Hide the stock add button - combined mode. Both are needed.
					"operation": "merge",
					"name": "CombinedModeAddRecordButton",
					"values": {
						"visible": { "bindTo": "SuBaseAddButtonVisible" }
					}
				}
			]/**SCHEMA_DIFF*/
		};
	});
