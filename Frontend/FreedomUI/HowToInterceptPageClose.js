define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to intercept the page close event ---------------------------
		// Handle crt.ClosePageRequest to run logic when the user tries to close
		// the page (back button, breadcrumb navigation, etc.).
		//
		// Call next?.handle(request) to let the close proceed normally.
		// Omit next?.handle(request) to cancel the close and keep the page open.
		//
		// Note: this intercepts the close, not dispatches it.
		// To close the page programmatically, see HowToClosePageFromHandler.js.

		handlers: /**SCHEMA_HANDLERS*/[

			// Intercept close - run logic before the page exits
			{
				request: "crt.ClosePageRequest",
				handler: async (request, next) => {
					// Code before the page closes (e.g. logging, cleanup)
					const name = await request.$context.PDS_Name_someAttr;
					console.log("Closing page, record name was: " + name);

					// Continue with the standard close
					return next?.handle(request);
				}
			},

			// Intercept close - cancel conditionally (do not call next)
			//
			// {
			//     request: "crt.ClosePageRequest",
			//     handler: async (request, next) => {
			//         const isDirty = await request.$context.SomeUnsavedFlag;
			//         if (isDirty) {
			//             // Cancel the close - page stays open
			//             return;
			//         }
			//         return next?.handle(request);
			//     }
			// }

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
