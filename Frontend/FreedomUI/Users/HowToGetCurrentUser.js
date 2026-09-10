define("YourPageSchema", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to get the current user info --------------------------------
		// Use sdk.SysValuesService to read system values including the currently
		// logged-in user's contact and account.
		//
		// sysValues.userContact - { value: Guid, displayValue: Name } of the user's Contact
		// sysValues.userAccount - { value: Guid, displayValue: Name } of the user's Account
		//
		// Requires: @creatio-devkit/common in SCHEMA_DEPS (sdk argument).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					await next?.handle(request);

					const sysValuesService = new sdk.SysValuesService();
					const sysValues = await sysValuesService.loadSysValues();

					const userContact = sysValues.userContact;
					const userAccount = sysValues.userAccount;

					// userContact.value        - Guid of the Contact record
					// userContact.displayValue - full name of the current user
					request.$context.MyAttribute = userContact.displayValue;

					// Use userContact.value to filter records by current user
					// e.g. pass to sdk.FilterGroup.addSchemaColumnFilterWithParameter
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
