define("UsrOrderSection", ["UsrOrderSectionResources"], function(resources) {
	return {
		entitySchemaName: "UsrOrder",
		messages: {
			"UsrOrderTotalChanged": {
				mode: Terrasoft.MessageMode.BROADCAST,
				direction: Terrasoft.MessageDirectionType.SUBSCRIBE
			}
		},
		details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,
		diff: /**SCHEMA_DIFF*/[
			{
				"operation": "insert",
				"name": "UsrRecalculateButton",
				"parentName": "ActionButtonsContainer",
				"propertyName": "items",
				"values": {
					"itemType": Terrasoft.ViewItemType.BUTTON,
					"caption": {"bindTo": "Resources.Strings.RecalculateButtonCaption"},
					"click": {"bindTo": "onRecalculateClick"},
					"style": Terrasoft.controls.ButtonEnums.style.DEFAULT
				}
			},
			{
				"operation": "merge",
				"name": "DataGrid",
				"values": {
					"activeRowAction": {"bindTo": "onActiveRowAction"}
				}
			}
		]/**SCHEMA_DIFF*/,
		methods: {
			/**
			 * @inheritdoc Terrasoft.BaseSectionV2#init
			 * @overridden
			 */
			init: function() {
				this.callParent(arguments);
				this.sandbox.subscribe("UsrOrderTotalChanged", this.onTotalChanged, this);
			},

			/**
			 * @private
			 */
			onTotalChanged: function() {
				this.reloadGridData();
			},

			/**
			 * @private
			 */
			onRecalculateClick: function() {
				var ids = this.getSelectedItems() || [];
				this.showInformationDialog(Ext.String.format(resources.localizableStrings.RecalculateMessage, ids.length));
			}
		}
	};
});
