define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to intercept the save event ---------------------------------
		// Handle crt.SaveRecordRequest to run logic before or after saving.
		//
		// Code before next?.handle -> executes before the platform saves.
		//   Fields set here are included in the same save operation.
		// Code after  next?.handle -> executes after the record is persisted.
		//
		// request.preventCardClose = true -> keeps the page open after save.
		//
		// To cancel the save: do not call next?.handle (page stays open,
		// nothing is persisted).

		handlers: /**SCHEMA_HANDLERS*/[

			// Before + after save
			{
				request: "crt.SaveRecordRequest",
				handler: async (request, next) => {
					// Before save: set values that should be persisted with the record
					const name = await request.$context.PDS_Name_h9kddsb;
					if (!name) {
						// Cancel save - do not call next
						return;
					}

					// Keep the page open after save (do not navigate back)
					request.preventCardClose = true;

					const result = await next?.handle(request);

					// After save: post-save logic (notifications, refresh, etc.)
					console.log("Record saved successfully");

					return result;
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
