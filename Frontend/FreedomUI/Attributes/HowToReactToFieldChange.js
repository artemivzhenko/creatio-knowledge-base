define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to react when a field value changes -------------------------
		// crt.HandleViewModelAttributeChangeRequest fires whenever any attribute
		// on the page changes.
		//
		// request.attributeName - name of the attribute that changed
		// request.silent        - true during page initialization; skip side-effects
		//
		// Always call next?.handle(request) so other handlers in the chain also
		// receive the change event.
		//
		// THERE IS A SECOND, DECLARATIVE WAY. An attribute can name its own
		// handler with the "change" key, and the request then fires only for that
		// attribute - no attributeName check needed:
		//
		//   "TypeField": {
		//       "modelConfig": { "path": "PDS.Type" },
		//       "change": { "request": "usr.OnTypeChange" }
		//   }
		//
		// Prefer that form when you know the attribute up front; it keeps one
		// handler per field instead of one growing switch. Use the request below
		// for GENERIC reactions - dirty tracking, logging, a rule over a list of
		// columns - or when the attribute set is not known at design time.
		// See HowToHandleAttributeChangeWithChangeKey.js.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelAttributeChangeRequest",
				handler: async (request, next) => {
					if (request.attributeName === "PDS_Name_h9kddsb" && !request.silent) {
						const name = await request.$context.PDS_Name_h9kddsb;

						// Update a computed attribute based on the new value
						request.$context.ComputedStatusText = name
							? "Name is set: " + name
							: "Name is empty";

						// Toggle visibility of a dependent element
						request.$context.IsStatusVisible = Boolean(name);
					}

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
