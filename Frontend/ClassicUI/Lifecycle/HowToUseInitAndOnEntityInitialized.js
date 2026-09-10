// --- Page lifecycle: init vs onEntityInitialized -----------------------------
// Order of the hooks you will override, and what is available in each:
//
//   init(callback, scope)
//       The view model exists; the ENTITY IS NOT LOADED YET. this.get("Id") and
//       any entity column return undefined here. Use init only for wiring:
//       sandbox subscriptions, server-channel listeners, module-level state,
//       DOM observers.
//
//   onEntityInitialized()
//       The record is loaded and every column is readable. This is where page
//       logic belongs: computing flags, defaulting values on a new record,
//       selecting the active tab, kicking off ESQ lookups.
//
//   destroy() / onDestroy()
//       The page is being disposed. Detach everything you attached in init.
//
// ALWAYS call this.callParent(arguments) first in an override. Skipping it
// breaks the base initialisation and the symptoms appear far from the cause.
//
// onEntityInitialized runs again after reloadEntity(), and can run more than
// once in a page's life. Make it idempotent: guard work that must happen only
// once with a flag.
//
// Detecting the mode inside onEntityInitialized:
//   this.isAddMode()   - a new record is being created
//   this.isCopyMode()  - the record is a copy of another one
//   this.isEditMode()  - an existing record is open
// Equivalent explicit form with ConfigurationEnums:
//   this.get("CardState") === enums.CardStateV2.ADD

define("QSMyEntity1Page", ["ConfigurationEnums"], function(enums) {

	var currentModule = null;

	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			init: function() {
				this.callParent(arguments);

				// Entity columns are NOT readable here.
				currentModule = this;
				this.factoriesInOrder = [];

				this.sandbox.subscribe("DashboardReloaded", this.onDashboardReloaded, this);
				this.sandbox.subscribe("QSDocumentTypeChange", this.onDocumentTypeChange,
					this, ["order-file"]);
				Terrasoft.ServerChannel.on(Terrasoft.EventName.ON_MESSAGE,
					this.onServerMessageReceived, currentModule);
			},

			onEntityInitialized: function() {
				this.callParent(arguments);

				// Now the record is available.
				this.checkUserRoles();
				this.setFieldRequirements();

				if (this.isAddMode() || this.isCopyMode()) {
					// Defaults that only apply to a brand-new record.
					this.getNextCode(function(code) {
						this.set("QSName", code);
					});
					if (this.get("QSAccount")) {
						this.onAccountChanged();
					}
				}

				// One-shot work, guarded against a second onEntityInitialized
				// after reloadEntity().
				if (!this.observersInitialised) {
					this.observersInitialised = true;
					this.startDomObservers();
				}
			},

			destroy: function() {
				// Detach the global listener attached in init.
				Terrasoft.ServerChannel.un(Terrasoft.EventName.ON_MESSAGE,
					this.onServerMessageReceived, currentModule);
				this.stopDomObservers();
				this.callParent(arguments);
			},

			onDashboardReloaded: function() {},
			onDocumentTypeChange: function() { this.set("IsChanged", true); },
			onServerMessageReceived: function(scope, message) {},
			checkUserRoles: function() {},
			setFieldRequirements: function() {},
			onAccountChanged: function() {},
			getNextCode: function(callback) { callback.call(this, "ORD-000001"); },
			startDomObservers: function() {},
			stopDomObservers: function() {}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
