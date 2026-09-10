define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to switch a validator on and off at runtime -------------------
		// $context exposes two methods for toggling a validator that is already
		// declared on an attribute:
		//
		//   request.$context.enableAttributeValidator("<AttributeName>", "<validatorKey>")
		//   request.$context.disableAttributeValidator("<AttributeName>", "<validatorKey>")
		//
		// The attribute name is the FULL generated name, the same one the view
		// element binds to - for example "SuRequestDS_SuEGRPOU_2l8nvsx", not the
		// column name "SuEGRPOU".
		//
		// The validator key is the one under which the validator is registered
		// on the attribute; "required" is the built-in one.
		//
		// WHEN TO USE THIS. Conditional mandatory fields: a field required only
		// for a particular record type or status. The declarative alternatives
		// are a `required` binding on the element, or a business rule; reach for
		// the imperative form when the condition needs a query or several
		// columns.
		//
		// Toggle BOTH ways. It is easy to write only the enable branch and end up
		// with a field that stays mandatory after the user switches the type
		// back, blocking the save with no visible reason.
		//
		// Call it from the change handler of the driving field so the state is
		// recalculated, and once more from the init handler so an already saved
		// record opens with the right state.
		//
		// See also HowToUseValidators.js for declaring the validators themselves.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[

			// Recalculate when the driving field changes.
			{
				request: "crt.HandleViewModelAttributeChangeRequest",
				handler: async (request, next) => {
					if (request.attributeName === "SuRequestDS_SuIsResident_k3n8dla") {
						await applyRequirements(request.$context);
					}
					return next?.handle(request);
				}
			},

			// And once when the page opens, so a saved record is correct too.
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					await next?.handle(request);
					await applyRequirements(request.$context);
					return;
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};

	// Both branches are written, so the state is always correct.
	async function applyRequirements($context) {
		const isResident = await $context.SuRequestDS_SuIsResident_k3n8dla;

		if (isResident) {
			$context.enableAttributeValidator("SuRequestDS_SuEGRPOU_2l8nvsx", "required");
			$context.disableAttributeValidator("SuRequestDS_SuINN_3x2r8ba", "required");
		} else {
			$context.disableAttributeValidator("SuRequestDS_SuEGRPOU_2l8nvsx", "required");
			$context.enableAttributeValidator("SuRequestDS_SuINN_3x2r8ba", "required");
		}
	}
});
