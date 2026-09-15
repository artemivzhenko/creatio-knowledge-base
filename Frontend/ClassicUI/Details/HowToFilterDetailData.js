// --- How to filter the rows a detail shows -----------------------------------
// THREE LEVELS, from the simplest to the most flexible.
//
// 1. THE MASTER FILTER - `filter` in the page `details` entry. This is the
//    default and covers most cases: show the rows whose detailColumn points at
//    this record.
//
//      "filter": { "detailColumn": "UsrMyEntity", "masterColumn": "Id" }
//
// 2. filterMethod - a METHOD ON THE PAGE that returns a Terrasoft.FilterGroup.
//    Declared next to `filter` in the same `details` entry:
//
//      "filterMethod": "ActivityFilter"
//
//    The method runs with the page view model as `this`, so it can read page
//    columns. It REPLACES the automatic master filter, so the master condition
//    has to be included yourself - forget it and the detail shows every record
//    in the table.
//
// 3. getFilters() inside the DETAIL schema - full control from the detail side,
//    when the condition belongs to the detail rather than to the page that
//    hosts it. See BaseMethods/DetailBaseMethods.js.
//
// Choose level 2 when the extra condition depends on page data, level 3 when
// the detail should behave the same wherever it is placed.

define("UsrMyEntity1Page", [], function() {
	return {
		entitySchemaName: "UsrMyEntity",

		details: /**SCHEMA_DETAILS*/{
			// Plain master filter.
			"Files": {
				"schemaName": "FileDetailV2",
				"entitySchemaName": "UsrMyEntityFile",
				"filter": {
					"detailColumn": "UsrMyEntity",
					"masterColumn": "Id"
				}
			},
			// Master filter PLUS a custom method.
			"Activities": {
				"schemaName": "ActivityDetailV2",
				"entitySchemaName": "Activity",
				"filter": {
					"detailColumn": "UsrMyEntity",
					"masterColumn": "Id"
				},
				"filterMethod": "ActivityFilter"
			}
		}/**SCHEMA_DETAILS*/,

		methods: {

			// Returns a FilterGroup. Note that the master condition is repeated
			// here: filterMethod replaces the automatic one.
			ActivityFilter: function() {
				var recordId = this.get("Id");
				var filterGroup = this.Terrasoft.createFilterGroup();

				filterGroup.add("MasterFilter",
					this.Terrasoft.createColumnFilterWithParameter(
						this.Terrasoft.ComparisonType.EQUAL, "UsrMyEntity", recordId));

				filterGroup.add("ActivityCategoryFilter",
					this.Terrasoft.createColumnFilterWithParameter(
						this.Terrasoft.ComparisonType.EQUAL, "ActivityCategory",
						"3b2f8c14-6d91-4a07-b5e3-9c1d47f0a862"));

				return filterGroup;
			}
		},

		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});

// --- Level 3: from inside the detail -----------------------------------------
// define("UsrMyDetail", [], function() {
//     return {
//         entitySchemaName: "Activity",
//         methods: {
//             getFilters: function() {
//                 var filterGroup = this.callParent(arguments);
//                 filterGroup.add("OnlyOpen",
//                     Terrasoft.createColumnFilterWithParameter(
//                         Terrasoft.ComparisonType.NOT_EQUAL, "Status",
//                         "4bdbb88f-58e6-df11-971b-001d60e938c6"));
//                 return filterGroup;
//             }
//         }
//     };
// });
