define("MyPage_FormPage", /**SCHEMA_DEPS*/["@creatio-devkit/common"]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/(sdk)/**SCHEMA_ARGS*/ {
	return {

		// --- Reference: stock crt.* requests ----------------------------------
		// A request is the unit of behaviour in Freedom UI. There are three ways
		// to trigger one:
		//
		//   1. declaratively from an element:
		//        "clicked": { "request": "crt.SomeRequest", "params": { ... } }
		//   2. imperatively from a handler:
		//        await request.$context.executeRequest({
		//            type: "crt.SomeRequest", $context: request.$context, ... });
		//   3. through the handler chain:
		//        await sdk.HandlerChainService.instance.process({
		//            type: "crt.SomeRequest", $context: request.$context, ... });
		//
		// You can also HANDLE any of these in `handlers` to extend or block the
		// stock behaviour - always finish with `return next?.handle(request)`
		// unless you deliberately cancel.
		//
		// ===================== RECORD LIFECYCLE ==============================
		//   crt.SaveRecordRequest            save the page record
		//   crt.CancelRecordChangesRequest   discard changes
		//   crt.CanDiscardUnsavedDataRequest  asked before leaving a dirty page;
		//                                    handle it to add your own guard
		//   crt.ClosePageRequest             close the page
		//   crt.CreateRecordFromLookupRequest  create a record straight from a
		//                                    lookup field ("+ create" action);
		//                                    usually wired with empty params
		//
		// ===================== NAVIGATION ====================================
		//   crt.OpenPageRequest        open a page:
		//                                params { schemaName, parameters }
		//                              parameters accept bindings ("$Name")
		//   crt.OpenLookupPageRequest  modal record picker; see
		//                              HowToOpenLookupPageAndCreateLinks.js
		//   crt.OpenLookupSourceRequest  open the source list of a lookup
		//
		// ===================== DATA ==========================================
		//   crt.LoadDataRequest              (re)load a data source; handle it to
		//                                    inject filters
		//   crt.DeleteRecordsRequest         delete rows:
		//                                    params { dataSourceName, filters }
		//   crt.ImportDataRequest            open the data import wizard
		//   crt.ExportDataGridToExcelRequest  params { viewName }
		//   crt.UploadFileRequest            params { viewElementName }
		//   crt.AddTagsInRecordsRequest      tag the selected rows
		//   crt.RemoveTagsInRecordsRequest   untag the selected rows
		//
		// ===================== PROCESS AND UI ================================
		//   crt.RunBusinessProcessRequest    see HowToRunBusinessProcessFromFrontend.js
		//   crt.ShowDialogRequest            see HowToShowDialog.js
		//
		// ===================== VIEW MODEL LIFECYCLE ==========================
		//   crt.HandleViewModelInitRequest        page initialisation; runs once
		//   crt.HandleViewModelInitializedRequest after initialisation finished
		//   crt.HandleViewModelAttributeChangeRequest
		//                                     an attribute changed; check
		//                                     request.attributeName to target one
		//   crt.HandleViewModelPauseRequest   the page is being suspended
		//   crt.HandleViewModelResumeRequest  the page is shown again
		//   crt.HandleViewModelDestroyRequest the view model is torn down
		//   crt.HandleViewModelEventRequest   generic view model event
		//   Pause/Resume - not Init/Destroy - is where GLOBAL listeners belong,
		//   because a page is paused far more often than it is destroyed. See
		//   HowToUsePauseAndResumeHandlers.js.
		//
		// ===================== NAMING YOUR OWN REQUESTS ======================
		// Custom requests use a package prefix instead of crt., and every
		// package in this repository sticks to its own:
		//   usr.*  the default Creatio prefix
		//   qs.*, dn.*, su.*, cfx.*  package-specific prefixes
		// Pick one prefix per package and keep it - a name collision between two
		// packages silently routes the request to the wrong handler.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Declarative: open another page and pass a bound value.
			{
				"operation": "insert",
				"name": "OpenChatButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(OpenChatButton_caption)#",
					"iconPosition": "only-text",
					"clicked": {
						"request": "crt.OpenPageRequest",
						"params": {
							"schemaName": "QSChatMiniPage",
							"parameters": { "SidebarTitle": "$Name" }
						}
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},

			// Declarative: export the rows of a named grid to Excel.
			{
				"operation": "insert",
				"name": "ExportButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(ExportButton_caption)#",
					"clicked": {
						"request": "crt.ExportDataGridToExcelRequest",
						"params": { "viewName": "GridDetail_jyzmfof" }
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 1
			},

			// Declarative: attach a file into a named FileList element.
			{
				"operation": "insert",
				"name": "UploadButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(UploadButton_caption)#",
					"clicked": {
						"request": "crt.UploadFileRequest",
						"params": { "viewElementName": "FileList_9ko9jdd" }
					}
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 2
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[

			// Imperative: run a stock request from your own code.
			{
				request: "usr.OpenRelatedPageRequest",
				handler: async (request, next) => {
					await request.$context.executeRequest({
						type: "crt.OpenPageRequest",
						$context: request.$context,
						schemaName: "QSOrder_FormPage",
						parameters: { recordId: await request.$context.PDS_OrderId_a1b2c3d }
					});
					return next?.handle(request);
				}
			},

			// Extending a stock request: add a guard, then let it continue.
			{
				request: "crt.CanDiscardUnsavedDataRequest",
				handler: async (request, next) => {
					const hasDraft = await request.$context.HasUnsentDraft;
					if (hasDraft) {
						// Returning without calling next cancels the navigation.
						return false;
					}
					return next?.handle(request);
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
