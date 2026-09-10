define("MyPage_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		// --- How to show attachments and upload a file -------------------------
		// crt.FileList renders the attachments of the page record. The upload
		// action is a stock request pointed at that element BY NAME:
		//
		//   "clicked": {
		//       "request": "crt.UploadFileRequest",
		//       "params": { "viewElementName": "FileList_9ko9jdd" }
		//   }
		//
		// viewElementName must match the `name` of the crt.FileList entry exactly.
		// A typo fails silently - the button does nothing and no error appears.
		//
		// The file list is backed by the <Entity>File table of the page entity,
		// wired through its own data source, so the record must be SAVED before
		// a file can be attached: an unsaved record has no id to attach to.
		//
		// CHECKING WHETHER FILES EXIST before allowing an action - for example
		// refusing to submit an application without a scan - is done by querying
		// the file entity with sdk.Model, not by reading the view element.
		//
		// The stock detail already offers add / delete / download in its own
		// toolbar; add a custom upload button only when you need the action
		// somewhere else on the page, such as in the header.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			{
				"operation": "insert",
				"name": "FileList_9ko9jdd",
				"values": {
					"type": "crt.FileList",
					"items": "$FileList_9ko9jdd",
					"visible": true,
					"fitContent": true
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},

			{
				"operation": "insert",
				"name": "UploadFileButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(UploadFileButton_caption)#",
					"iconPosition": "only-text",
					"clicked": {
						"request": "crt.UploadFileRequest",
						// Must match the FileList element name above.
						"params": { "viewElementName": "FileList_9ko9jdd" }
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 1
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[

			// Refuse an action while the record has no attachments.
			{
				request: "usr.SubmitForApprovalRequest",
				handler: async (request, next) => {
					const recordId = await request.$context.PDS_Id_a1b2c3d;

					const fileModel = await sdk.Model.create("QSRequestFile");
					const files = await fileModel.load({
						attributes: ["Id"],
						parameters: [{
							type: sdk.ModelParameterType.Filter,
							value: await (new sdk.FilterGroup()).addSchemaColumnFilterWithParameter(
								sdk.ComparisonType.Equal, "QSRequest", recordId)
						}]
					});

					if (!files.length) {
						const dialogService = new sdk.DialogService();
						await dialogService.open({
							message: await request.$context.Resources.Strings.NoFilesAttachedMessage,
							actions: [
								{ key: "OK", config: { color: "primary", caption: "OK" } }
							]
						});
						// Stop here: do not pass the request on.
						return;
					}

					return next?.handle(request);
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
