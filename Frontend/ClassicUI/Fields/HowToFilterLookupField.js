// --- How to filter a lookup field --------------------------------------------
// Declare `lookupListConfig` on the lookup column in `attributes`. The filters
// array holds FUNCTIONS that are called with the view model as `this` every
// time the lookup list is opened, so they can read other columns and return a
// different filter each time.
//
//   lookupListConfig: {
//       filters: [ function() { ... return filterGroup; } ],
//       columns: ["QSCode"],        // extra columns to load into the list
//       orders:  [{ columnPath: "Name" }]
//   }
//
// Building the filter:
//   var filters = Ext.create("Terrasoft.FilterGroup");
//   filters.logicalOperation = Terrasoft.LogicalOperatorType.AND;   // or .OR
//   filters.add("<uniqueKey>", Terrasoft.createColumnFilterWithParameter(
//       Terrasoft.ComparisonType.EQUAL, "<ColumnPath>", <value>));
//
// The first argument of add() is a key inside the group; reusing a key silently
// overwrites the previous filter, so keys must be unique (that is why loops
// append an index: "RoleFilter" + i).
//
// Return an EMPTY FilterGroup to show everything. Returning null or undefined
// breaks the lookup list.
//
// ComparisonType values used most: EQUAL, NOT_EQUAL, IS_NULL, IS_NOT_NULL,
// GREATER, LESS, CONTAIN, START_WITH.
// Column paths may traverse references: "QSService.QSProductType".

define("QSMyEntity1Page", [], function() {

	const MethodDirectImport = "7ec276fe-1e76-46f6-a14c-a368a2d4aa5a";
	const GroupNonResident   = "1014c1f8-fd3d-4a11-a67c-5ac0b697f892";
	const AccountTypeClient  = "d34b9da2-53e6-df11-971b-001d60e938c6";

	return {
		entitySchemaName: "QSMyEntity",
		attributes: {

			// Filter that depends on another column of the same page.
			"QSSeller": {
				"dataValueType": Terrasoft.DataValueType.LOOKUP,
				"lookupListConfig": {
					"filters": [function() {
						var filters = Ext.create("Terrasoft.FilterGroup");
						filters.logicalOperation = Terrasoft.LogicalOperatorType.AND;

						var method = this.get("QSMethodRegistration");
						if (method && method.value === MethodDirectImport) {
							filters.add("NonResidentOnly",
								Terrasoft.createColumnFilterWithParameter(
									Terrasoft.ComparisonType.EQUAL,
									"QSCounterpartyGroup", GroupNonResident));
						} else {
							filters.add("AccountType",
								Terrasoft.createColumnFilterWithParameter(
									Terrasoft.ComparisonType.EQUAL,
									"Type", AccountTypeClient));
							filters.add("CounterpartyGroup",
								Terrasoft.createColumnFilterWithParameter(
									Terrasoft.ComparisonType.EQUAL,
									"QSCounterpartyGroup", GroupNonResident));
						}
						return filters;
					}]
				}
			},

			// Whitelist of allowed ids, built from an array. Note the OR group
			// and the unique key per iteration.
			"QSContainerType": {
				"dataValueType": Terrasoft.DataValueType.LOOKUP,
				"dependencies": [
					{ "columns": ["QSDownloadType"], "methodName": "onDownloadTypeChanged" }
				],
				"lookupListConfig": {
					"filters": [function() {
						var filters = Ext.create("Terrasoft.FilterGroup");
						var downloadType = this.get("QSDownloadType");

						// No driver value yet -> show the full list.
						if (!downloadType || !downloadType.value) {
							return filters;
						}

						var allowedIds = ["bb5a4641-7e1f-443f-bd9e-037529edca3d",
							"b086dbde-084f-4b15-80fa-7ff6204b4441",
							"7ba595be-0394-40d5-a5b3-d17e75adff57"];

						filters.logicalOperation = Terrasoft.LogicalOperatorType.OR;
						allowedIds.forEach(function(id, index) {
							filters.add("Allowed" + index,
								Terrasoft.createColumnFilterWithParameter(
									Terrasoft.ComparisonType.EQUAL, "Id", id));
						});
						return filters;
					}]
				}
			}
		},
		methods: {

			onDownloadTypeChanged: function() {
				// The dependent lookup may now hold a value that the new filter
				// forbids - clear it so the user re-picks.
				this.set("QSContainerType", null);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
