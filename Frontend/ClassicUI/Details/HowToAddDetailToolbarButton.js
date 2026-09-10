// --- How to add a button to the detail toolbar -------------------------------
// SOURCE: DoneFinancialLogisticsRedefined/QSSchema9f0e3f06Detail and
// DonePackageUpdated/QSSchemac88cf5d1Detail.
//
// A detail has its own command strip. Target it with:
//
//   "parentName":   "Detail"
//   "propertyName": "tools"
//
// "tools" is the third and last propertyName Creatio uses in diff - the other
// two are "items" (controls in a container) and "tabs" (tabs of a tab panel).
//
// The button config is the normal one: itemType BUTTON, caption, click, style.
// Styles come from Terrasoft.controls.ButtonEnums.style - BLUE, GREEN, GREY,
// RED, TRANSPARENT, DEFAULT.
//
// Replacing the stock "+" entirely: remove "AddRecordButton" and insert your
// own button into tools.
//
// READING THE MASTER RECORD from a detail: this.get("MasterRecordId") - a base
// attribute of BaseDetailV2. It is the usual parameter for a process started
// from the detail toolbar.
//
// Refresh after the action: this.updateDetail() from inside the detail, or
// this.loadGridData() when you only need the rows re-read.
//
// PITFALL - executeProcess has NO trailing callback parameter. The callback and
// its scope go INSIDE the config object. Code written as
//     ProcessModuleUtilities.executeProcess(config, function(){...}, this)
// compiles and starts the process, but the function is silently ignored, so the
// "finished" dialog never appears. Put it in config.callback instead - the
// correct form is shown below. See Processes/HowToRunBusinessProcess.js.

define("QSMyDetail", ["ProcessModuleUtilities"], function(ProcessModuleUtilities) {
	return {
		entitySchemaName: "QSLinkOrderApplicationFL",
		details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,

		diff: /**SCHEMA_DIFF*/[
			{
				// Drop the stock add button.
				"operation": "remove",
				"name": "AddRecordButton"
			},
			{
				// Own button in the detail toolbar.
				"operation": "insert",
				"name": "CustomProcessButton",
				"values": {
					"itemType": Terrasoft.ViewItemType.BUTTON,
					"caption": { "bindTo": "Resources.Strings.AddLinkButtonCaption" },
					"click": { "bindTo": "runCustomProcess" },
					"style": Terrasoft.controls.ButtonEnums.style.GREY
				},
				"parentName": "Detail",
				"propertyName": "tools",
				"index": 0
			},
			{
				// A second toolbar button, in the accent style.
				"operation": "insert",
				"name": "CreateSellerRequestButton",
				"values": {
					"itemType": Terrasoft.ViewItemType.BUTTON,
					"caption": { "bindTo": "Resources.Strings.CreateSellerRequestCaption" },
					"click": { "bindTo": "onCreateSellerRequestClick" },
					"style": Terrasoft.controls.ButtonEnums.style.BLUE,
					"visible": true
				},
				"parentName": "Detail",
				"propertyName": "tools",
				"index": 1
			}
		]/**SCHEMA_DIFF*/,

		methods: {

			// Fire and forget: the master id is the only parameter.
			runCustomProcess: function() {
				var masterRecordId = this.get("MasterRecordId");
				if (!masterRecordId) {
					return;
				}
				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_c4ea6fc_9fc733b",
					parameters: { recordId: masterRecordId }
				});
			},

			// With feedback: mask, callback INSIDE the config, refresh on success.
			onCreateSellerRequestClick: function() {
				var self = this;
				var masterRecordId = this.get("MasterRecordId");

				Terrasoft.MaskHelper.ShowBodyMask();

				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSRequestSeller",
					parameters: { Service: masterRecordId },
					// Keeps the process start out of the browser history, so the
					// URL does not change under the user.
					skipHistoryState: true,
					callback: function(request, success, response) {
						Terrasoft.MaskHelper.HideBodyMask();

						if (!success) {
							self.showInformationDialog(
								self.get("Resources.Strings.ProcessFailedMessage"));
							return;
						}
						self.showInformationDialog(
							self.get("Resources.Strings.ProcessFinishedMessage"));
						self.updateDetail();
					},
					scope: this
				});
			}
		}
	};
});
