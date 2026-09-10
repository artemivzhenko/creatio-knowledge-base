// --- How to declare a view model attribute -----------------------------------
// `attributes` declares observable columns of the page view model. Two kinds:
//
//   1. Entity columns    - the key matches a column of entitySchemaName. You
//                          declare it only to attach extra behaviour (change
//                          dependencies, lookup filters, required flag).
//   2. Virtual columns   - the key does not exist on the entity. It lives only
//                          in the browser and is used to drive the UI (enable /
//                          visible flags, computed captions, temporary state).
//
// Supported keys inside an attribute:
//
//   dataValueType     - Terrasoft.DataValueType.*, tells the framework how to
//                       store and render the value.
//   type              - Terrasoft.ViewModelColumnType.*; use VIRTUAL_COLUMN for
//                       a column that must never be sent to the server.
//   value             - initial value.
//   isRequired        - static required flag (dynamic: see Fields/).
//   dependencies      - recalculation hooks (see HowToReactToFieldChange.js).
//   lookupListConfig  - lookup filtering (see Fields/HowToFilterLookupField.js).
//   caption           - display caption for virtual columns bound to controls.
//
// Numeric Terrasoft.DataValueType values you will meet in generated code:
//   0  GUID          1  TEXT        4  INTEGER    5  FLOAT      6  MONEY
//   7  DATE_TIME     8  DATE        9  TIME       10 LOOKUP     11 ENUM
//   12 BOOLEAN       15 CUSTOM_OBJECT
// Prefer the symbolic form (Terrasoft.DataValueType.BOOLEAN) in hand-written code.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		attributes: {

			// Virtual boolean used to enable/disable a button in diff.
			"CreateFreightKPButtonEnabled": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN,
				"value": false
			},

			// Virtual boolean that never reaches the server.
			"IsEditable": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN,
				"type": Terrasoft.ViewModelColumnType.VIRTUAL_COLUMN,
				"value": true
			},

			// Free-form object state (DOM observers, cached collections...).
			"CurrentObserver": {
				"dataValueType": Terrasoft.DataValueType.CUSTOM_OBJECT,
				"value": null
			},

			// Plain text constant used by page logic.
			"TargetTabSelector": {
				"dataValueType": Terrasoft.DataValueType.TEXT,
				"value": "li[data-item-index=\"18\"]"
			},

			// An entity column redeclared only to attach a change dependency.
			"QSAccount": {
				"dependencies": [
					{
						"columns": ["QSAccount"],
						"methodName": "onQSAccountChanged"
					}
				]
			},

			// A pseudo-attribute used purely as a listener host. Its own value is
			// never read; it exists so that changes to the listed columns trigger
			// the method. This is the idiomatic Classic UI way to react to
			// several columns at once.
			"FieldRequirementsManager": {
				"dependencies": [
					{
						"columns": ["QSStatus", "QSMethodRegistration"],
						"methodName": "setFieldRequirements"
					}
				]
			}
		},
		methods: {

			onQSAccountChanged: function() {
				var account = this.get("QSAccount");
				console.log("account changed", account && account.value);
			},

			setFieldRequirements: function() {
				// Recalculate which fields are mandatory for the current status.
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
