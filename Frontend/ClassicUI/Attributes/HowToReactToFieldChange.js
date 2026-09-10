// --- How to react to a field change ------------------------------------------
// Classic UI has three ways to run code when a column changes. Use them in this
// order of preference.
//
// 1. attributes[...].dependencies  - declarative, the standard way.
//      columns:    array of column names to watch.
//      methodName: name of a method in `methods`, called with no arguments.
//    The attribute that HOSTS the dependency does not have to be one of the
//    watched columns. Pages routinely declare a dummy attribute whose only job
//    is to host a dependency over several real columns.
//
// 2. this.on("change:ColumnName", handler, this) - imperative subscription,
//    normally set up in init or onEntityInitialized. Use when the set of columns
//    is dynamic, or when you must unsubscribe later.
//
// 3. onColumnNameChanged - conventional method name some base schemas call.
//    Do not rely on it unless the parent schema declares it.
//
// Important: dependencies fire on EVERY change, including the ones your own
// code makes with this.set(). Guard against recursion when a handler writes
// back into a watched column.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		attributes: {

			// One watched column -> one handler.
			"QSService": {
				"dependencies": [
					{
						"columns": ["QSService"],
						"methodName": "onQSServiceChange"
					}
				]
			},

			// Several watched columns -> one handler. The attribute name is just
			// a label; it carries no value of its own.
			"AccountClientRequirement": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN,
				"dependencies": [
					{
						"columns": ["QSStatus", "QSMethodRegistration"],
						"methodName": "setAccountClientRequirement"
					}
				]
			},

			// A long watch list is normal when the page auto-saves once every
			// mandatory field is filled in.
			"RequiredFieldsToAutoSave": {
				"dependencies": [
					{
						"columns": ["QSName", "QSOrderDate", "QSOrganization", "QSAccount",
							"QSCurrency", "QSOwner", "QSTypeCargo", "QSActualWeight"],
						"methodName": "autoSaveWhenRequiredFieldsAreFilled"
					}
				]
			}
		},
		methods: {

			init: function() {
				this.callParent(arguments);
				// Imperative alternative to `dependencies`.
				this.on("change:QSAmount", this.onAmountChanged, this);
			},

			onQSServiceChange: function() {
				var service = this.get("QSService");
				if (!service || !service.value) {
					return;
				}
				// Clear dependent fields when the driving lookup changes.
				this.set("QSDownloadType", null);
			},

			setAccountClientRequirement: function() {
				var status = this.get("QSStatus");
				this.set("AccountClientRequirement",
					!!status && status.value === "f6c25e34-63f3-4b6d-9769-db0f37d42f0e");
			},

			autoSaveWhenRequiredFieldsAreFilled: function() {
				// Guard: do not re-enter while a save is already running.
				if (this.get("IsAutoSaving")) {
					return;
				}
			},

			onAmountChanged: function() {
				console.log("amount", this.get("QSAmount"));
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
