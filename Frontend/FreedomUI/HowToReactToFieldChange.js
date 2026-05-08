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
