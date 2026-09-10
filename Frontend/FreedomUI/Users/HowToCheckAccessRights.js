define("MyPage_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		// --- How to check the user's access rights ----------------------------
		// sdk.RightsService answers whether the current user may execute a SYSTEM
		// OPERATION (the "Operation permissions" section in system settings):
		//
		//   const rightsService = new sdk.RightsService();
		//   const canDo = await rightsService.getCanExecuteOperation("<OperationCode>");
		//
		// The argument is the operation CODE, not its caption.
		//
		// The call is asynchronous, so the answer cannot be used directly in a
		// binding. Store it in a view model attribute and bind the UI to that
		// attribute - the same pattern as the role check in Classic UI.
		//
		// Run it in the init handler so the page opens in the right state.
		//
		// THIS IS A UI CONVENIENCE, NOT SECURITY. Hiding a button stops nobody
		// from issuing the request another way. Enforce the permission on the
		// server as well - in the business process, the web service, or the
		// entity event listener that does the actual work. See
		// Backend/C#/HowToManageRecordAccessRights.cs.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				// The button appears only when the operation is granted.
				"operation": "insert",
				"name": "ApproveCalculationButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(ApproveCalculationButton_caption)#",
					"iconPosition": "only-text",
					"visible": "$IsAccessRightsGranted",
					"clicked": { "request": "usr.ApproveCalculationRequest", "params": {} }
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},
			{
				// Or keep it visible but disabled.
				"operation": "merge",
				"name": "AmountInput",
				"values": {
					"readonly": "$IsAccessRightsGranted | crt.InvertBooleanValue"
				}
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					"IsAccessRightsGranted": { "value": false }
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					const rightsService = new sdk.RightsService();

					// Access permission for the system operation.
					const canView = await rightsService.getCanExecuteOperation(
						"QSCanViewComplexCalculationsForApproval");

					request.$context.IsAccessRightsGranted = canView;

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
