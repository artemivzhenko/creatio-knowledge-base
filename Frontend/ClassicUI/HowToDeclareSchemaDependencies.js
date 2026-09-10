// --- How to declare schema dependencies (AMD define) -------------------------
// Classic UI schemas are AMD modules. The second argument of define() is the
// dependency list; the function arguments receive the resolved modules IN THE
// SAME ORDER. Dependencies that only have a side effect (CSS) take no argument.
//
// Frequently used dependencies:
//
//   "ProcessModuleUtilities"         - run business processes from the client.
//   "ConfigurationEnums"             - card state enums (ADD / EDIT / COPY).
//   "LookupUtilities"                - open a lookup selection window.
//   "ConfigurationGrid",
//   "ConfigurationGridGenerator",
//   "ConfigurationGridUtilitiesV2"   - required to make a detail inline-editable.
//   "css!QSMyPageCSS"                - loads a CSS-only Module schema. The "css!"
//                                      plugin takes no argument, so put it LAST
//                                      and the argument order stays aligned.
//   "@creatio-devkit/common"         - only in Module schemas that register a
//                                      custom view element (Freedom UI interop).
//
// Anything declared above the returned object (constants, module-level state)
// is shared by every instance of the schema in the browser session. That is why
// pages often keep `var currentModule = null;` and assign `this` to it in init:
// detached callbacks (DOM handlers, server messages) can then reach the view
// model. Prefer passing scope explicitly where you can - module-level state
// leaks between records opened in the same session.

define("QSMyEntity1Page",
	["ProcessModuleUtilities", "ConfigurationEnums", "LookupUtilities", "css!QSMyEntity1PageCSS"],
	function(ProcessModuleUtilities, enums, LookupUtilities) {

		// Module-level constants: lookup values used by the page logic.
		// Classic UI code addresses lookups by GUID, so give them names.
		const StatusInWork   = "f6c25e34-63f3-4b6d-9769-db0f37d42f0e";
		const StatusCanceled = "ac84a45a-8bc2-496b-be63-2f45aeb58db3";

		// Lookup values are objects, not scalars.
		const Yes = { value: "c92c530c-027a-48ae-ba5c-93e7dcbed661", displayValue: "Yes" };
		const No  = { value: "d5b0df38-08d9-48a0-b25f-929ddb513713", displayValue: "No" };

		// Shared reference to the currently initialised view model.
		var currentModule = null;

		return {
			entitySchemaName: "QSMyEntity",
			attributes: {},
			methods: {

				init: function() {
					this.callParent(arguments);
					currentModule = this;
				},

				onRunProcessClick: function() {
					ProcessModuleUtilities.executeProcess({
						sysProcessName: "QSProcess_2da82f9",
						parameters: { orderId: this.get("Id") }
					});
				},

				isNewRecord: function() {
					return this.get("CardState") === enums.CardStateV2.ADD;
				}
			},
			diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
		};
	});
