// --- How to write a mixin module and use it on a page ------------------------
// A mixin is a client schema of type Module whose body defines an Ext class in
// the Terrasoft.configuration.mixins namespace with a short alternateClassName,
// and returns an instance of it. A page lists it in `mixins` and its methods
// then run AS THE PAGE'S OWN: `this` is the page's view model, so this.get(),
// this.set(), this.sandbox and this.showInformationDialog all work inside it.
//
// The three places that must agree, or the page silently gets no methods:
//   1. Ext.define("Terrasoft.configuration.mixins.UsrMyMixin", {
//          alternateClassName: "Terrasoft.UsrMyMixin", ... })
//   2. the page:  mixins: { UsrMyMixin: "Terrasoft.UsrMyMixin" }
//   3. the page's define() dependencies list "UsrMyMixin" - without it the
//      class is not loaded yet when the page is built ("Terrasoft.UsrMyMixin is
//      not a constructor" in the console, or nothing at all).
//
// Strings of the mixin live in its own UsrMyMixinResources (depend on it in the
// mixin's define); a page string is not visible to the mixin's resources.
// Name the methods with the mixin's prefix (usrMyMixinPrint, not print): a page
// or a parent method of the same name wins, and the mixin's one is never called.
// A method of the page calls the mixin's by name, like its own:
// this.usrMyMixinPrint(). To extend a page method, keep it on the page and
// call into the mixin from there; a mixin cannot callParent into the page.
//
// Package files: `python scaffold.py module <pkg> UsrMyMixin --mixin` writes
// this module; `python classicui.py add-mixin <pkg> <Page> UsrMyMixin` adds 2 and
// 3 to a page (no-code/tools).

// ======================= THE MIXIN (schema UsrMyMixin, type Module) =========
define("UsrMyMixin", ["UsrMyMixinResources"], function(resources) {
	Ext.define("Terrasoft.configuration.mixins.UsrMyMixin", {
		alternateClassName: "Terrasoft.UsrMyMixin",

		// Runs with the page's view model as `this`.
		usrMyMixinPrint: function() {
			var recordId = this.get("Id");
			if (!recordId) {
				this.showInformationDialog(resources.localizableStrings.UsrSaveFirstMessage);
				return;
			}
			this.callService({
				serviceName: "UsrMyService",
				methodName: "Print",
				data: {recordId: recordId}
			}, function(response) {
				this.set("UsrPrintedOn", new Date());
				this.showInformationDialog(response.PrintResult || resources.localizableStrings.UsrPrintedMessage);
			}, this);
		},

		// A helper the page binds a button's visibility to.
		usrMyMixinIsPrintVisible: function() {
			return !this.isNewMode();
		}
	});
	return Ext.create("Terrasoft.UsrMyMixin");
});

// ======================= THE PAGE THAT USES IT =================================
define("UsrMyEntity1Page", ["UsrMyMixin"], function() {
	return {
		entitySchemaName: "UsrMyEntity",
		mixins: {
			UsrMyMixin: "Terrasoft.UsrMyMixin"
		},
		methods: {
			// A page method reaches the mixin's by name.
			onPrintClick: function() {
				this.usrMyMixinPrint();
			}
		},
		diff: /**SCHEMA_DIFF*/[
			{
				"operation": "insert",
				"name": "UsrPrintButton",
				"parentName": "LeftContainer",
				"propertyName": "items",
				"values": {
					"itemType": Terrasoft.ViewItemType.BUTTON,
					"caption": {"bindTo": "Resources.Strings.UsrPrintButtonCaption"},
					"click": {"bindTo": "onPrintClick"},
					"visible": {"bindTo": "usrMyMixinIsPrintVisible"}
				}
			}
		]/**SCHEMA_DIFF*/
	};
});
