// --- How to open a lookup selection window from code -------------------------
// Add "LookupUtilities" to the schema dependencies and call:
//
//   LookupUtilities.Open(sandbox, config, callback, scope,
//                        multiSelectDefaultValue, hideActions, useNewLookup);
//
// Arguments as used in practice:
//   sandbox   - always this.sandbox
//   config    - what to show (see below)
//   callback  - invoked with the selection result
//   scope     - execution scope for the callback, normally `this`
//   the trailing flags are usually passed as null / false
//
// config keys:
//   entitySchemaName - the entity to pick from (required)
//   multiSelect      - true allows several rows
//   hideActions      - hide the "new record" actions in the window
//   columns          - extra columns to display in the list
//   filters          - a Terrasoft.FilterGroup restricting the choices
//   lookupPostfix    - suffix appended to the window id, needed when the same
//                      page opens more than one lookup window
//
// The CALLBACK receives an object with `selectedRows`, a Terrasoft.Collection:
//
//   function(result) {
//       var items = result.selectedRows.getItems();   // array of view models
//       var first = items[0];
//       var id      = first.get("Id");
//       var caption = first.get("Name");
//   }
//
// Even with multiSelect false the result is a COLLECTION - take element 0.
//
// Use this when the user must pick a record that is not bound to a column on
// the page (adding a row to a custom detail, picking a target for an action).
// For a normal lookup column, do not open the window yourself: bind the control
// and filter it with lookupListConfig instead.

define("QSMyEntity1Page", ["LookupUtilities"], function(LookupUtilities) {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Pick a single account.
			onAddFactoryClick: function() {
				var config = {
					entitySchemaName: "Account",
					hideActions: true,
					multiSelect: false
				};
				LookupUtilities.Open(this.sandbox, config, this.onFactorySelected, this,
					null, false, false);
			},

			onFactorySelected: function(result) {
				var items = result.selectedRows.getItems();
				if (!items.length) {
					return;
				}
				var account = items[0];
				this.set("QSFactory", {
					value: account.get("Id"),
					displayValue: account.get("Name")
				});
			},

			// Multi-select with a pre-applied filter.
			onAddContactsClick: function() {
				var filters = Ext.create("Terrasoft.FilterGroup");
				filters.add("ActiveOnly", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSIsActive", true));

				var config = {
					entitySchemaName: "Contact",
					multiSelect: true,
					columns: ["Name", "Email"],
					filters: filters,
					lookupPostfix: "ContactPicker"
				};
				LookupUtilities.Open(this.sandbox, config, this.onContactsSelected, this,
					null, false, false);
			},

			onContactsSelected: function(result) {
				var contactIds = result.selectedRows.getItems().map(function(item) {
					return item.get("Id");
				});
				this.linkContacts(contactIds);
			},

			linkContacts: function(contactIds) {}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
