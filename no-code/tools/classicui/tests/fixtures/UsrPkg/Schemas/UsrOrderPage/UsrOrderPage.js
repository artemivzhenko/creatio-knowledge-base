define("UsrOrderPage", ["BusinessRuleModule", "ConfigurationConstants", "UsrOrderPageResources"],
	function(BusinessRuleModule, ConfigurationConstants, resources) {
		return {
			entitySchemaName: "UsrOrder",
			messages: {
				/**
				 * Published when the order total changes {so the section can refresh}.
				 */
				"UsrOrderTotalChanged": {
					mode: Terrasoft.MessageMode.BROADCAST,
					direction: Terrasoft.MessageDirectionType.PUBLISH
				}
			},
			mixins: {
				UsrPrintMixin: "Terrasoft.UsrPrintMixin"
			},
			attributes: {
				"UsrStatus": {
					lookupListConfig: {
						columns: ["Name", "Description"],
						orders: [{columnPath: "Name"}]
					}
				},
				"UsrTotal": {
					dataValueType: Terrasoft.DataValueType.FLOAT,
					dependencies: [
						{
							columns: ["UsrAmount", "UsrDiscount"],
							methodName: "recalculateTotal"
						}
					]
				}
			},
			details: /**SCHEMA_DETAILS*/{
				"UsrOrderProductDetail": {
					"schemaName": "UsrOrderProductDetailV2",
					"entitySchemaName": "UsrOrderProduct",
					"filter": {
						"detailColumn": "UsrOrder",
						"masterColumn": "Id"
					}
				},
				"Files": {
					"schemaName": "FileDetailV2",
					"entitySchemaName": "UsrOrderFile",
					"filter": {
						"detailColumn": "UsrOrder",
						"masterColumn": "Id"
					}
				},
				"UsrOrderHistoryDetail": {
					"schemaName": "UsrOrderHistoryDetailV2",
					"filter": {
						"detailColumn": "UsrOrder",
						"masterColumn": "Id"
					}
				}
			}/**SCHEMA_DETAILS*/,
			modules: /**SCHEMA_MODULES*/{}/**SCHEMA_MODULES*/,
			businessRules: /**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/,
			methods: {
				/**
				 * @inheritdoc Terrasoft.BasePageV2#onEntityInitialized
				 * @overridden
				 */
				onEntityInitialized: function() {
					this.callParent(arguments);
					if (this.isNewMode()) {
						this.set("UsrDate", new Date());
					}
				},

				/**
				 * Total = amount minus discount; a "}" in a string must not end the method.
				 * @private
				 */
				recalculateTotal: function() {
					var amount = this.get("UsrAmount") || 0;
					var discount = this.get("UsrDiscount") || 0;
					this.set("UsrTotal", amount - discount);
					this.sandbox.publish("UsrOrderTotalChanged", {total: amount - discount}, ["}"]);
				},

				/**
				 * Order numbers look like ORD-0001 (the regex holds a brace and a quote).
				 * @private
				 */
				isNumberValid: function(value) {
					return /^ORD-\d{4}["']?$/.test(value || "");
				},

				/**
				 * @inheritdoc Terrasoft.BasePageV2#setValidationConfig
				 * @overridden
				 */
				setValidationConfig: function() {
					this.callParent(arguments);
					this.addColumnValidator("UsrNumber", this.validateNumber);
				},

				/**
				 * @private
				 */
				validateNumber: function(value) {
					var message = this.isNumberValid(value) ? "" : resources.localizableStrings.NumberFormatMessage;
					return {invalidMessage: message};
				},

				/**
				 * @private
				 */
				onPrintClick: function() {
					this.printOrder(this.get("Id"));
				},

				/**
				 * @private
				 */
				isPrintVisible: function() {
					return !this.isNewMode() && this.get("UsrStatus") !== null;
				},

				/**
				 * @private
				 */
				getStatusCaption: function() {
					var status = this.get("UsrStatus");
					return status ? status.displayValue : "";
				},

				onUsrDiscountChange: Terrasoft.emptyFn
			},
			diff: /**SCHEMA_DIFF*/[
				{
					"operation": "insert",
					"name": "UsrNumber",
					"values": {
						"layout": {"colSpan": 24, "rowSpan": 1, "column": 0, "row": 0},
						"bindTo": "UsrNumber"
					},
					"parentName": "ProfileContainer",
					"propertyName": "items",
					"index": 0
				},
				{
					"operation": "insert",
					"name": "UsrStatus",
					"values": {
						"layout": {"colSpan": 24, "rowSpan": 1, "column": 0, "row": 1},
						"bindTo": "UsrStatus",
						"contentType": Terrasoft.ContentType.ENUM
					},
					"parentName": "ProfileContainer",
					"propertyName": "items",
					"index": 1
				},
				{
					"operation": "insert",
					"name": "UsrInfoTab",
					"values": {
						"caption": {"bindTo": "Resources.Strings.UsrInfoTabCaption"},
						"items": []
					},
					"parentName": "Tabs",
					"propertyName": "tabs",
					"index": 0
				},
				{
					"operation": "insert",
					"name": "UsrInfoContainer",
					"values": {
						"itemType": Terrasoft.ViewItemType.GRID_LAYOUT,
						"items": []
					},
					"parentName": "UsrInfoTab",
					"propertyName": "items",
					"index": 0
				},
				{
					"operation": "insert",
					"parentName": "UsrInfoContainer",
					"propertyName": "items",
					"values": {
						"name": "UsrAmount",
						"bindTo": "UsrAmount",
						"layout": {"colSpan": 12, "rowSpan": 1, "column": 0, "row": 0}
					}
				},
				{
					"operation": "insert",
					"parentName": "UsrInfoContainer",
					"propertyName": "items",
					"values": {
						"name": "UsrDiscount",
						"bindTo": "UsrDiscount",
						"layout": {"colSpan": 12, "rowSpan": 1, "column": 12, "row": 0},
						"change": {"bindTo": "onUsrDiscountChange"}
					}
				},
				{
					"operation": "insert",
					"name": "UsrTotal",
					"values": {
						"layout": {"colSpan": 12, "rowSpan": 1, "column": 0, "row": 1},
						"bindTo": "UsrTotal",
						"enabled": false
					},
					"parentName": "UsrInfoContainer",
					"propertyName": "items",
					"index": 2
				},
				{
					"operation": "insert",
					"name": "UsrOrderProductDetail",
					"values": {
						"itemType": Terrasoft.ViewItemType.DETAIL,
						"markerValue": "added-detail"
					},
					"parentName": "UsrInfoTab",
					"propertyName": "items",
					"index": 1
				},
				{
					"operation": "insert",
					"name": "Files",
					"values": {
						"itemType": Terrasoft.ViewItemType.DETAIL
					},
					"parentName": "UsrInfoTab",
					"propertyName": "items",
					"index": 2
				},
				{
					"operation": "insert",
					"name": "UsrPrintButton",
					"values": {
						"itemType": Terrasoft.ViewItemType.BUTTON,
						"caption": {"bindTo": "Resources.Strings.PrintButtonCaption"},
						"click": {"bindTo": "onPrintClick"},
						"visible": {"bindTo": "isPrintVisible"},
						"style": Terrasoft.controls.ButtonEnums.style.BLUE
					},
					"parentName": "LeftContainer",
					"propertyName": "items",
					"index": 5
				},
				{
					"operation": "insert",
					"name": "UsrCloseButton",
					"values": {
						"itemType": Terrasoft.ViewItemType.BUTTON,
						"caption": {"bindTo": "Resources.Strings.CloseButtonCaption"},
						"click": {"bindTo": "onCloseClick"}
					},
					"parentName": "LeftContainer",
					"propertyName": "items",
					"index": 6
				},
				{
					"operation": "merge",
					"name": "ESNTab",
					"values": {
						"order": 3
					}
				},
				{
					"operation": "move",
					"name": "UsrStatus",
					"parentName": "Header",
					"propertyName": "items",
					"index": 0
				},
				{
					"operation": "remove",
					"name": "NotesAndFilesTab"
				}
			]/**SCHEMA_DIFF*/,
			rules: {
				"UsrStatus": {
					"UsrStatusRequired": {
						"ruleType": BusinessRuleModule.enums.RuleType.BINDPARAMETER,
						"property": BusinessRuleModule.enums.Property.REQUIRED,
						"conditions": [{
							"leftExpression": {
								"type": BusinessRuleModule.enums.ValueType.ATTRIBUTE,
								"attribute": "UsrNumber"
							},
							"comparisonType": Terrasoft.ComparisonType.IS_NOT_NULL
						}]
					}
				}
			}
		};
	}
);
