define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "OpenSectionButton",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Button",
					"caption": "Open section",
					"iconPosition": "only-text",
					"clicked": {
						"request": "usr.OpenSectionRequest",
						"params": {}
					}
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to navigate to another section or page ----------------------
		// Use Terrasoft.workspaceBaseUrl to build an absolute URL and open it
		// via window.open().
		//
		// URL pattern for sections:
		//   /Shell/#SectionModuleV2/SectionSchemaName
		//
		// "_blank" opens in a new tab; use "_self" to navigate in the current tab.
		// .focus() brings the new tab to the foreground (browser may block it).

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.OpenSectionRequest",
				handler: async (request, next) => {
					const url = Terrasoft.workspaceBaseUrl + "/Shell/#SectionModuleV2/SysAdminOperationSectionV2";
					window.open(url, "_blank").focus();

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
