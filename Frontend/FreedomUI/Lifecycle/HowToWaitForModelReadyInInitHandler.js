define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to wait for the model to actually be loaded ------------------
		// crt.HandleViewModelInitRequest fires before the page's own record data
		// has loaded. Two problems follow directly from that:
		//   - Reading an attribute here returns undefined - it isn't populated yet.
		//   - Setting an attribute here gets silently overwritten once Creatio
		//     loads the record's default data afterwards.
		// Old workarounds used setTimeout; since Creatio 8.1.3 subscribe to
		// request.$context.events$ instead and wait for the
		// "finish-load-model-attributes" event.
		//
		// evt.payload has boolean flags per attribute (true/false), NOT the
		// actual values - only fields that are actually on the page appear in
		// it at all, so always check the field's flag is present before
		// reading/writing that field.
		//
		// getPrimaryModelMode() tells you "create" (new record) vs "update"
		// (existing record) - the two need different handling below.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					await next?.handle(request);

					request.$context.events$.subscribe(async (evt) => {
						const modelMode = await request.$context.getPrimaryModelMode();
						const attributesLoaded = evt?.type === "finish-load-model-attributes";

						// Reading a value safely once it has actually loaded (edit mode)
						if (modelMode === "update" && attributesLoaded &&
							evt?.payload?.UsrName && evt?.payload?.Id) {
							const recordId = await request.$context.Id;
							const name = await request.$context.UsrName;
						}

						// Setting a default value that will NOT get overwritten (create mode)
						if (modelMode === "create" && attributesLoaded && evt?.payload?.UsrName) {
							request.$context.UsrName = "New record";
						}
					});
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
