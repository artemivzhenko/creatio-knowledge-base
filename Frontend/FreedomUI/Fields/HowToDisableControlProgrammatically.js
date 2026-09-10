define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// Field bound to a boolean attribute that controls its readonly state,
		// plus the lookup field whose value drives that attribute.
		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"name": "Type",
				"values": {
					// The attribute means "enabled", but readonly needs the opposite,
					// so invert it here. Alternatively name the attribute
					// "IsTypeDisabled" and bind it directly with no converter.
					"readonly": "$IsTypeEnabled | crt.InvertBooleanValue"
				}
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					"IsTypeEnabled": { "value": true }
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to programmatically disable/enable a control -----------------
		// Business rules can't cover every case (e.g. disabling a field based on
		// data read from another record via a model query). For those cases:
		//   1. Add a boolean attribute (viewModelConfigDiff, above).
		//   2. Bind the control's readonly/disabled property to that attribute
		//      (viewConfigDiff, above).
		//   3. Set the attribute from a change handler, below.
		//
		// readonly vs disabled: both work; readonly shows a lock icon on the
		// field, disabled does not.
		//
		// This handler also runs during initial page load with
		// request.silent === true, which is what applies the correct state as
		// soon as the record's data has loaded - no separate init handler needed.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelAttributeChangeRequest",
				handler: async (request, next) => {
					if (request.attributeName === "Type") {
						request.$context.IsTypeEnabled = !request.value ||
							request.value.displayValue !== "Customer";
					}
					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
