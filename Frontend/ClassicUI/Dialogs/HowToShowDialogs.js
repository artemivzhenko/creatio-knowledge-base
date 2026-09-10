// --- How to show information and confirmation dialogs ------------------------
// Both are methods of the view model, so call them with `this`:
//
//   this.showInformationDialog(message, [callback], [config])
//       One OK button. Use for notifications and blocking explanations.
//
//   this.showConfirmationDialog(message, callback, buttons, [scope])
//       message  - text to show
//       callback - function(returnCode) called with the pressed button
//       buttons  - array of button codes: ["yes", "no"], ["ok", "cancel"],
//                  or ["Ok"] for a single-button dialog
//
// The callback receives a RETURN CODE, compared against
// Terrasoft.MessageBoxButtons.<BUTTON>.returnCode:
//   Terrasoft.MessageBoxButtons.YES.returnCode
//   Terrasoft.MessageBoxButtons.NO.returnCode
//   Terrasoft.MessageBoxButtons.OK.returnCode
//   Terrasoft.MessageBoxButtons.CANCEL.returnCode
//
// Outside a view model (a plain module, a DOM handler that lost scope) use the
// global forms: Terrasoft.showConfirmation(message, callback, buttons, scope)
// and Terrasoft.showInformation(message).
//
// Dialogs are asynchronous. Everything that depends on the answer must live
// inside the callback - code after the call runs immediately, before the user
// has clicked anything.
//
// Reporting a server error: passing result.errorInfo.message into a
// single-button confirmation is the idiom this codebase uses for failures,
// because it renders long messages better than the information dialog.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Plain notification.
			warnUnsavedRecord: function() {
				this.showInformationDialog(
					this.get("Resources.Strings.SaveRecordFirstMessage"));
			},

			// Yes / No question.
			confirmDeletion: function(itemCaption, onConfirmed) {
				var self = this;
				this.showConfirmationDialog(
					Ext.String.format(this.get("Resources.Strings.ConfirmDeleteMessage"), itemCaption),
					function(returnCode) {
						if (returnCode === Terrasoft.MessageBoxButtons.YES.returnCode) {
							onConfirmed.call(self);
						}
					},
					["yes", "no"]);
			},

			// Single-button dialog used to surface a server error.
			showServerError: function(result) {
				this.showConfirmationDialog(result.errorInfo.message, function() {}, ["Ok"]);
			},

			// Global form, for use where `this` is not the view model.
			confirmFromDetachedHandler: function(self) {
				Terrasoft.showConfirmation(
					"Add cargo dimensions now?",
					function(returnCode) {
						if (returnCode === Terrasoft.MessageBoxButtons.YES.returnCode) {
							self.openCargoModal();
						}
					},
					["yes", "no"],
					self);
			},

			openCargoModal: function() {}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
