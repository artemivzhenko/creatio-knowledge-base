define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to use the page init handler --------------------------------
		// crt.HandleViewModelInitRequest fires once when the page ViewModel is
		// being set up - before the page is fully rendered.
		//
		// Always call next FIRST so the platform finishes its own initialization
		// and populates DataSource attributes before your code reads them.
		//
		// Use the init handler to:
		//   - Set initial attribute values
		//   - Read loaded entity data and drive UI state
		//   - Inject startup data or configuration

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					// Let the platform finish its initialization first
					await next?.handle(request);

					// DataSource attributes are populated after next resolves
					const name = await request.$context.PDS_Name_h9kddsb;

					// Set boolean attributes to control initial UI state
					request.$context.IsFormReadonly  = false;
					request.$context.IsButtonVisible = Boolean(name);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
