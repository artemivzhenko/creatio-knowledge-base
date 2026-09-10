// --- How to read the current URL, record id and the page the user came from --
// Classic UI routes through the URL hash, which makes it a reliable source of
// truth when the view model is not (yet) trustworthy:
//
//   window.location.href  - full URL
//   window.location.hash  - "#/QSMyEntity1Page/edit/<guid>" style route
//
// WHY THIS MATTERS. Callbacks and DOM handlers can fire after the user has
// navigated away, and they still hold a reference to the old view model. The
// guard used in this codebase compares the guid in the hash with the record the
// callback belongs to, and bails out when they differ:
//
//   var activeRecordId = window.location.hash.match(/[a-f0-9-]{36}/);
//   if (activeRecordId && activeRecordId[0] !== this.get("Id")) { return; }
//
// Combine it with this.destroyed, which the framework sets when the view model
// is disposed. Check both before touching the model from a deferred callback.
//
// REMEMBERING WHERE THE USER CAME FROM. There is no framework API for the
// previous page, so pages write a marker into sessionStorage before navigating
// and read it in onEntityInitialized. Remove the marker after reading it,
// otherwise the behaviour repeats on the next open.
//
// sessionStorage is per browser tab and survives a page transition inside the
// app; localStorage would leak the marker across sessions.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			onEntityInitialized: function() {
				this.callParent(arguments);
				this.applyPreviousPageBehaviour();
			},

			// Open a specific tab when the user arrived from a workplace list.
			applyPreviousPageBehaviour: function() {
				var previousPage = sessionStorage.getItem("previousPage");

				if (previousPage &&
					(previousPage.indexOf("QSLogistWorkplace") > -1 ||
					 previousPage.indexOf("QSCCKAndManagersDesk") > -1)) {
					this.setActiveTab("NotesAndFilesTab");
					// Consume the marker so it applies only once.
					sessionStorage.removeItem("previousPage");
				}
			},

			// Write the marker before navigating away from a list page.
			rememberCurrentPage: function() {
				sessionStorage.setItem("previousPage", window.location.hash);
			},

			// Guard for a deferred callback: is this page still the active one?
			isStillActive: function() {
				if (this.destroyed) {
					return false;
				}
				var currentId = this.get("Id");
				var match = window.location.hash.match(/[a-f0-9-]{36}/);
				return !match || match[0] === currentId;
			},

			// Typical use in a deferred handler.
			onDeferredCheck: function() {
				if (!this.isStillActive()) {
					return;
				}
				this.set("SomeFlag", true);
			},

			// Environment check, e.g. to disable an action outside production.
			isProductionEnvironment: function() {
				return window.location.href.indexOf("creatio.done.partners") > -1;
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
