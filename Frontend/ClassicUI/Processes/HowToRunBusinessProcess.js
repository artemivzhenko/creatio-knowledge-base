// --- How to run a business process from a Classic UI page --------------------
// Add "ProcessModuleUtilities" to the schema dependencies and call
// executeProcess with a config object:
//
//   ProcessModuleUtilities.executeProcess({
//       sysProcessName:       "<process code>",   // the CODE, not the caption
//       parameters:           { paramName: value, ... },
//       resultParameterNames: ["Out1", "Out2"],   // optional
//       callback:             function(request, success, response) { ... },
//       scope:                this                // optional
//   });
//
// sysProcessName is the process CODE from the process designer (for example
// "QSProcess_2da82f9"), not its display name. You can also start a process by
// id with `sysProcessId`.
//
// parameters: keys must match the INPUT parameter names of the process exactly,
// and they are case sensitive. Pass lookup values as a RAW guid string, not as
// { value, displayValue }.
//
// The call is fire-and-forget unless you pass a callback. Without one you get no
// signal at all - not even a failure. For anything the user waits on, either
// pass a callback, or have the process push a message back to the client (see
// Messaging/HowToReceiveServerMessages.js), which is the pattern this codebase
// uses for long-running processes.
//
// The callback signature is (request, success, response). Reading output
// parameters from `response` is version-dependent and brittle; the reliable
// route for returning data to the page is a server message or a re-read with
// ESQ after the process completes.
//
// A process usually works on the SAVED record. Check this.get("Id") first, and
// save the page before starting the process if the record is new.

define("QSMyEntity1Page", ["ProcessModuleUtilities"], function(ProcessModuleUtilities) {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Simplest form: start and forget.
			onCreateComplexKPButtonClick: function() {
				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_2da82f9",
					parameters: {
						orderId: this.get("Id")
					}
				});
			},

			// Guarded form with a callback and a re-entrancy flag, so a double
			// click cannot start the process twice.
			cancelOrder: function() {
				var self = this;
				var orderId = this.get("Id");

				if (!orderId) {
					this.showInformationDialog(this.get("Resources.Strings.SaveRecordFirstMessage"));
					return;
				}
				if (this.isCancelProcessRunning) {
					return;
				}
				this.isCancelProcessRunning = true;
				Terrasoft.MaskHelper.ShowBodyMask();

				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_2201f91",
					parameters: {
						orderId: orderId
					},
					resultParameterNames: ["processInstanceId"],
					callback: function(request, success, response) {
						self.isCancelProcessRunning = false;
						Terrasoft.MaskHelper.HideBodyMask();

						if (!success) {
							self.showInformationDialog(
								self.get("Resources.Strings.ProcessFailedMessage"));
							return;
						}
						// The process result is delivered by a server message;
						// here we only re-read the record.
						self.reloadEntity();
					},
					scope: this
				});
			},

			// Passing several parameters, including lookups as raw guids.
			startShipmentProcess: function() {
				var status = this.get("QSStatus");

				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_45350ac",
					parameters: {
						orderId:   this.get("Id"),
						statusId:  status ? status.value : null,
						comment:   this.get("QSGeneralComment") || "",
						isUrgent:  !!this.get("QSIsUrgent")
					}
				});
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
