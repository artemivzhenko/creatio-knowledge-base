// --- How to make a detail editable inline (ConfigurationGrid) ----------------
// A stock detail opens a separate edit page for every row. To edit rows in place
// you replace the DataGrid with Terrasoft.ConfigurationGrid and mix in
// ConfigurationGridUtilitiesV2. This is the canonical Classic UI editable detail
// and the shape below is what the Detail Wizard generates.
//
// Required parts, all four:
//   1. dependencies  "ConfigurationGrid", "ConfigurationGridGenerator",
//                    "ConfigurationGridUtilitiesV2"
//   2. attribute     "IsEditable" - virtual boolean, value true
//   3. mixins        ConfigurationGridUtilitiesV2
//   4. diff merge on "DataGrid" with className, generator and the row actions
//
// The methods referenced by bindTo (generateActiveRowControlsConfig, changeRow,
// unSelectRow, onGridClick, initActiveRowKeyMap) all come from the mixin - you
// do not implement them. Only onActiveRowAction is re-declared, so you have a
// hook to intercept the row buttons before delegating to the mixin.
//
// Row action tags are fixed strings the mixin understands:
//   "save", "cancel", "card", "copy", "remove".
// Their icons come from stock resources: Resources.Images.SaveIcon, CancelIcon,
// CardIcon, CopyIcon, RemoveIcon.

define("QSMyDetail", ["ConfigurationGrid", "ConfigurationGridGenerator",
	"ConfigurationGridUtilitiesV2"], function() {
	return {
		entitySchemaName: "QSServicesInOrder",

		attributes: {
			"IsEditable": {
				dataValueType: Terrasoft.DataValueType.BOOLEAN,
				type: Terrasoft.ViewModelColumnType.VIRTUAL_COLUMN,
				value: true
			}
		},

		mixins: {
			ConfigurationGridUtilitiesV2: "Terrasoft.ConfigurationGridUtilitiesV2"
		},

		methods: {

			// Intercept a row action, then hand it to the mixin implementation.
			onActiveRowAction: function(buttonTag, primaryColumnValue) {
				if (buttonTag === "remove" && !this.canDeleteRow(primaryColumnValue)) {
					this.showInformationDialog(this.get("Resources.Strings.CannotDeleteMessage"));
					return;
				}
				this.mixins.ConfigurationGridUtilitiesV2.onActiveRowAction.call(
					this, buttonTag, primaryColumnValue);
			},

			canDeleteRow: function(recordId) {
				return true;
			}
		},

		diff: /**SCHEMA_DIFF*/[
			{
				"operation": "merge",
				"name": "DataGrid",
				"values": {
					"className": "Terrasoft.ConfigurationGrid",
					"generator": "ConfigurationGridGenerator.generatePartial",
					"generateControlsConfig": { "bindTo": "generateActiveRowControlsConfig" },
					"changeRow":    { "bindTo": "changeRow" },
					"unSelectRow":  { "bindTo": "unSelectRow" },
					"onGridClick":  { "bindTo": "onGridClick" },
					"activeRowActions": [
						{
							"className": "Terrasoft.Button",
							"style": this.Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
							"tag": "save",
							"markerValue": "save",
							"imageConfig": { "bindTo": "Resources.Images.SaveIcon" }
						},
						{
							"className": "Terrasoft.Button",
							"style": this.Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
							"tag": "cancel",
							"markerValue": "cancel",
							"imageConfig": { "bindTo": "Resources.Images.CancelIcon" }
						},
						{
							"className": "Terrasoft.Button",
							"style": this.Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
							"tag": "card",
							"markerValue": "card",
							"imageConfig": { "bindTo": "Resources.Images.CardIcon" }
						},
						{
							"className": "Terrasoft.Button",
							"style": Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
							"tag": "copy",
							"markerValue": "copy",
							"imageConfig": { "bindTo": "Resources.Images.CopyIcon" }
						},
						{
							"className": "Terrasoft.Button",
							"style": this.Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
							"tag": "remove",
							"markerValue": "remove",
							"imageConfig": { "bindTo": "Resources.Images.RemoveIcon" }
						}
					],
					"initActiveRowKeyMap": { "bindTo": "initActiveRowKeyMap" },
					"activeRowAction":     { "bindTo": "onActiveRowAction" },
					"multiSelect":         { "bindTo": "MultiSelect" }
				}
			}
		]/**SCHEMA_DIFF*/
	};
});
