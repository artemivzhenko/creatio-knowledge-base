// --- How to read and write the businessRules section -------------------------
// `businessRules` is the declarative block the page designer generates. It is
// stored as numbers, so this file is mainly a decoder ring for reading and
// hand-editing what the designer produced.
//
// SHAPE:
//   businessRules: {
//       "<ColumnName>": {                 // the column the rule acts on
//           "<RuleKey>": {                // designer guid or a readable name
//               "uId": "<guid>",          // stable id of the rule
//               "enabled": true,          // false = kept but inactive
//               "removed": false,         // true = tombstone in a replacing schema
//               "ruleType": 0,            // see below
//               ...type-specific keys
//           }
//       }
//   }
//
// ruleType (Terrasoft.RuleTypes):
//   0  BINDPARAMETER  set a UI property of the column from a condition
//   1  FILTRATION     filter a lookup column by another column
//
// BINDPARAMETER keys:
//   property   which UI property is driven:
//                0 VISIBLE   1 ENABLED   2 REQUIRED   3 READONLY
//   logical    how conditions combine: 0 AND, 1 OR
//   conditions array of { comparisonType, leftExpression, rightExpression }
//
// Expression shape:
//   type            0 CONSTANT (has "value"), 1 ATTRIBUTE (has "attribute")
//   dataValueType   10 LOOKUP, 12 BOOLEAN, 1 TEXT, 4 INTEGER ...
//   attribute       column name, for type 1
//   attributePath   optional path INTO the referenced record, e.g.
//                   attribute "Status" + attributePath "Finish" reads
//                   Status.Finish
//   value           literal, for type 0
//
// comparisonType: 3 EQUAL, 4 NOT_EQUAL (use Terrasoft.ComparisonType in code).
//
// FILTRATION keys:
//   baseAttributePatch  column path on the LOOKUP entity to compare
//   attribute           column on THIS page providing the value
//   comparisonType      usually 3 (EQUAL)
//   autoClean           clear the column when the filter stops matching
//   autocomplete        auto-select when exactly one value remains
//
// WHEN TO USE WHAT. A business rule is the cheapest way to drive
// visible/enabled/required from a simple condition - no code, and it survives
// schema regeneration. Reach for JS (attributes + dependencies) when the
// condition needs a query, arithmetic, or more than a couple of columns.
// Do not implement the same rule in both places: they will fight.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",

		businessRules: /**SCHEMA_BUSINESS_RULES*/{

			// BINDPARAMETER: make QSCheckedSB visible when the counterparty
			// group is one of two values (logical = 1 -> OR).
			"QSCheckedSB": {
				"efe0ed83-6e1e-40c1-baf6-16603830e2df": {
					"uId": "efe0ed83-6e1e-40c1-baf6-16603830e2df",
					"enabled": true,
					"removed": false,
					"ruleType": 0,        // BINDPARAMETER
					"property": 0,        // VISIBLE
					"logical": 1,         // OR
					"conditions": [
						{
							"comparisonType": 3,   // EQUAL
							"leftExpression":  { "type": 1, "dataValueType": 10,
												 "attribute": "QSCounterpartyGroup" },
							"rightExpression": { "type": 0, "dataValueType": 10,
												 "value": "517cb8f2-ae35-45f0-a8b8-a3af8bd6192c" }
						},
						{
							"comparisonType": 3,
							"leftExpression":  { "type": 1, "dataValueType": 10,
												 "attribute": "QSCounterpartyGroup" },
							"rightExpression": { "type": 0, "dataValueType": 10,
												 "value": "1014c1f8-fd3d-4a11-a67c-5ac0b697f892" }
						}
					]
				}
			},

			// BINDPARAMETER on ENABLED, reading through a reference:
			// "enabled while Status.Finish is not true".
			"Result": {
				"BindParameterEnabledResultToStatus": {
					"uId": "0f361b3b-aca5-468d-9235-4e05dc984486",
					"enabled": true,
					"ruleType": 0,
					"property": 1,        // ENABLED
					"logical": 0,         // AND
					"conditions": [
						{
							"comparisonType": 3,
							"leftExpression":  { "type": 1, "dataValueType": 12,
												 "attribute": "Status",
												 "attributePath": "Finish" },
							"rightExpression": { "type": 0, "value": true }
						}
					]
				}
			},

			// FILTRATION: only contracts of the selected account, disabled for now.
			"QSBasicContract": {
				"86cb5577-7d80-4105-bf73-9210af082df0": {
					"uId": "86cb5577-7d80-4105-bf73-9210af082df0",
					"enabled": false,
					"removed": false,
					"ruleType": 1,        // FILTRATION
					"baseAttributePatch": "Account",
					"comparisonType": 3,  // EQUAL
					"autoClean": false,
					"autocomplete": false,
					"type": 1,            // ATTRIBUTE
					"attribute": "IsCardOpenedAttribute"
				}
			}
		}/**SCHEMA_BUSINESS_RULES*/,

		methods: {},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
