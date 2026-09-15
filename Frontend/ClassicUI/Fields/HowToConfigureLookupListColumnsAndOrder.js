// --- How to sort a lookup list and load extra columns ------------------------
// lookupListConfig accepts more than `filters`:
//
//   filters  [Function]  functions returning a FilterGroup; called with the view
//                        model as `this` every time the list opens
//                        (see HowToFilterLookupField.js)
//   orders   [Object]    sort order of the list:
//                          { columnPath: "Name",
//                            direction: Terrasoft.OrderDirection.asc }
//                        Several entries sort by several columns, in order.
//   columns  [String]    extra columns to LOAD with each row of the lookup list.
//                        They are fetched with the list, so the selection window
//                        and the list's own filters can use them.
//
// Terrasoft.OrderDirection.asc / .desc are the direction constants.
//
// DO NOT ASSUME the extra columns are readable off the SELECTED value. What
// this.get("MyLookup") returns is { value, displayValue }; whether anything else
// rides along depends on the control and the Creatio version, so do not rely
// on it. When a change handler needs a related field, re-read it with an ESQ -
// that is the form shown below.
//
// Sorting a lookup by a technical column (a position or weight column) is the
// usual way to control the order of a short dictionary without renaming its
// records.

define("UsrMyEntity1Page", [], function() {
	return {
		entitySchemaName: "UsrMyEntity",
		attributes: {

			// Sort the currency list by a position column, descending.
			"UsrCurrency": {
				"lookupListConfig": {
					"orders": [
						{
							"columnPath": "CurrecySymbolPosition",
							"direction": Terrasoft.OrderDirection.desc
						}
					]
				}
			},

			// Filter + sort + preload extra columns.
			"UsrService": {
				"dataValueType": Terrasoft.DataValueType.LOOKUP,
				"dependencies": [
					{ "columns": ["UsrService"], "methodName": "onServiceChanged" }
				],
				"lookupListConfig": {
					"filters": [function() {
						var filters = Ext.create("Terrasoft.FilterGroup");
						filters.add("ActiveOnly", Terrasoft.createColumnFilterWithParameter(
							Terrasoft.ComparisonType.EQUAL, "UsrIsActive", true));
						return filters;
					}],
					"orders": [
						{ "columnPath": "UsrPosition", "direction": Terrasoft.OrderDirection.asc },
						{ "columnPath": "Name", "direction": Terrasoft.OrderDirection.asc }
					],
					// Loaded with the row, readable after selection.
					"columns": ["UsrProductType", "UsrDefaultCurrency"]
				}
			}
		},

		methods: {

			onServiceChanged: function() {
				var service = this.get("UsrService");
				if (!service || !service.value) {
					return;
				}
				// The selected value carries only { value, displayValue }, so
				// read the related column with an ESQ.
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "UsrService"
				});
				esq.addColumn("UsrDefaultCurrency");
				esq.getEntity(service.value, function(result) {
					if (!result.success || !result.entity) {
						return;
					}
					var defaultCurrency = result.entity.get("UsrDefaultCurrency");
					if (defaultCurrency) {
						this.set("UsrCurrency", defaultCurrency);
					}
				}, this);
			}
		},

		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
