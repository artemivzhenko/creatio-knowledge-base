// --- How to let the user pick an entity COLUMN (structure explorer) ----------
// SOURCE: _SalesUp_DT_ITSM - BaseLookupSection and SuChangeLogCaseSettingPageV2.
//
// When a record must store the NAME of a column rather than a value (log
// settings, dynamic filters, column mapping tables), open the structure
// explorer instead of writing your own picker:
//
//   this.Terrasoft.StructureExplorerUtilities.open({
//       moduleName:   "StructureExploreModuleV2",
//       moduleConfig: {
//           schemaName:   "Case",   // the entity whose columns are browsed
//           useBackwards: true,     // allow reverse (one-to-many) references
//           displayId:    true      // show Id columns in the tree
//       },
//       handlerMethod: this.onColumnSelected,   // called with the picked item
//       scope:         this
//   });
//
// Add "StructureExplorerUtilities" to the schema dependencies.
//
// THE SELECTED ITEM carries:
//   item.columnPath                 dotted path to the column
//   item.leftExpressionColumnPath   same path, older property name - read both
//   item.leftExpressionCaption      localized caption of the column
//   item.dataValueType              numeric Terrasoft.DataValueType
//
// LOOKUP COLUMNS need the "Id" suffix. A picked lookup returns the path of the
// reference itself; to store something a query can use you append "Id":
//
//   isLookup = dataValueType === Terrasoft.DataValueType.LOOKUP ||
//              dataValueType === Terrasoft.DataValueType.IMAGELOOKUP
//   columnName = isLookup ? columnPath + "Id" : columnPath
//
// Reopening the explorer after a rejected pick (duplicate, wrong type) is the
// friendly behaviour: the user stays in the flow instead of clicking the button
// again.

define("SuChangeLogCaseSettingPageV2", ["StructureExplorerUtilities"], function() {
	return {
		entitySchemaName: "SuChangeLogCaseSetting",
		methods: {

			// Bound from the right icon of the field - see
			// Diff/HowToUseControlConfigAndConverters.js
			openColumnExplorer: function() {
				var schemaName = "Case";
				if (Ext.isEmpty(schemaName)) {
					return;
				}
				this.Terrasoft.StructureExplorerUtilities.open({
					moduleName: "StructureExploreModuleV2",
					moduleConfig: {
						schemaName: schemaName,
						useBackwards: true,
						displayId: true
					},
					handlerMethod: this.onColumnSelected,
					scope: this
				});
			},

			onColumnSelected: function(item) {
				if (!item || !Ext.isObject(item)) {
					return;
				}
				var dataValueType = item.dataValueType;
				var isLookup = dataValueType != null &&
					(dataValueType === Terrasoft.DataValueType.LOOKUP ||
						dataValueType === Terrasoft.DataValueType.IMAGELOOKUP);

				// Both property names appear depending on the Creatio version.
				var columnPath = item.columnPath || item.leftExpressionColumnPath;
				var columnName = isLookup ? columnPath + "Id" : columnPath;
				var columnCaption = item.leftExpressionCaption || columnName;

				this.set("SuBpmColumnName", columnName);
				this.set("SuBpmColumnCaption", columnCaption);
			},

			// Reject duplicates and send the user straight back to the explorer.
			onColumnSelectedWithDuplicateCheck: function(item) {
				var columnName = item.columnPath || item.leftExpressionColumnPath;
				var columnCaption = item.leftExpressionCaption || columnName;

				this.findExistingColumn(columnName, function(isExists) {
					if (isExists) {
						this.showInformationDialog(
							this.get("Resources.Strings.SuColumnAlreadyAddedCaption") +
							" " + columnCaption);
						this.openColumnExplorer();
						return;
					}
					this.set("SuBpmColumnName", columnName);
					this.set("SuBpmColumnCaption", columnCaption);
				});
			},

			findExistingColumn: function(columnName, callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "SuChangeLogCaseSetting"
				});
				esq.addColumn("Id");
				esq.filters.add("byColumnName", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "SuBpmColumnName", columnName));
				esq.getEntityCollection(function(result) {
					callback.call(this, result.success && result.collection.getCount() > 0);
				}, this);
			},

			// Turning a numeric dataValueType back into its name. `_` (lodash)
			// is available globally in Classic UI.
			getTypeNameByNumber: function(number) {
				var key = _.findKey(Terrasoft.DataValueType, function(value) {
					return value === number;
				});
				return key ? key : "";
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
