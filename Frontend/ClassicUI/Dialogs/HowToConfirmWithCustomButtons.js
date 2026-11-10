// --- How to ask a question with custom buttons (also inside asyncValidate) ----
// showConfirmationDialog takes button CONFIGS as well as the codes "yes"/"no":
// copy a standard button with Ext.apply and give it your caption and your own
// returnCode. The callback receives that returnCode - compare with it, not with
// Terrasoft.MessageBoxButtons.YES.returnCode.
//
//   var saveButton = Ext.apply({}, Terrasoft.MessageBoxButtons.YES,
//       {caption: "Save anyway", returnCode: "UsrSaveAnyway"});
//   this.showConfirmationDialog(message, callback, [saveButton, "cancel"]);
//
// Keep `this` in a variable (var self = this) for the callback: do not count
// on the dialog calling it with the view model as its scope.
//
// INSIDE asyncValidate (the save pipeline, see Lifecycle/HowToInterceptSaveAndValidate):
// the page has already shown the body mask for the save, so a dialog opened
// there renders BEHIND the grey overlay and the page looks frozen. Call
// this.hideBodyMask() (or Terrasoft.MaskHelper.HideBodyMask()) before the
// dialog. Then answer the pipeline exactly once from the dialog's callback:
//   - the user confirms -> callback.call(scope, response) and the save goes on
//   - the user declines -> callback.call(scope, {success: false}) - with no
//     message, so no second dialog; the save stops quietly
// Forgetting to call back on one of the buttons leaves the save hanging with no
// error anywhere.
//
// Strings come from the page's resources (Resources.Strings.<Name>); a caption
// literal like the one above is for the illustration only.

define("UsrMyEntity1Page", [], function() {
	return {
		entitySchemaName: "UsrMyEntity",
		methods: {

			// A question with three answers of your own.
			askHowToClose: function() {
				var self = this;
				var saveButton = Ext.apply({}, Terrasoft.MessageBoxButtons.YES, {
					caption: this.get("Resources.Strings.UsrSaveAndCloseCaption"),
					returnCode: "UsrSaveAndClose"
				});
				var discardButton = Ext.apply({}, Terrasoft.MessageBoxButtons.NO, {
					caption: this.get("Resources.Strings.UsrDiscardCaption"),
					returnCode: "UsrDiscard"
				});
				this.showConfirmationDialog(this.get("Resources.Strings.UsrUnsavedChangesMessage"), function(returnCode) {
					if (returnCode === "UsrSaveAndClose") {
						self.save();
					} else if (returnCode === "UsrDiscard") {
						self.onCloseClick();
					}
					// "cancel": nothing to do.
				}, [saveButton, discardButton, "cancel"]);
			},

			// A confirmation that can stop the save.
			asyncValidate: function(callback, scope) {
				this.callParent([function(response) {
					if (!this.validateResponse(response)) {
						return;
					}
					if (this.get("UsrAmount") <= this.get("UsrLimit")) {
						callback.call(scope, response);
						return;
					}
					this.hideBodyMask(); // otherwise the dialog sits behind the save's mask
					var continueButton = Ext.apply({}, Terrasoft.MessageBoxButtons.YES, {
						caption: this.get("Resources.Strings.UsrSaveOverLimitCaption"),
						returnCode: "UsrSaveOverLimit"
					});
					this.showConfirmationDialog(this.get("Resources.Strings.UsrOverLimitMessage"), function(returnCode) {
						if (returnCode === "UsrSaveOverLimit") {
							callback.call(scope, response);
						} else {
							callback.call(scope, {success: false});
						}
					}, [continueButton, "cancel"]);
				}, this]);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
