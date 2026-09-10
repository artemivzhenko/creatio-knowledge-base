// --- How to receive a message pushed from the server -------------------------
// Server code (a script task, a web service, an event listener) can push a
// message to the browser with MsgChannelUtilities.PostMessage. On the Classic UI
// side you listen on Terrasoft.ServerChannel:
//
//   Terrasoft.ServerChannel.on(Terrasoft.EventName.ON_MESSAGE, handler, scope);
//
// The handler receives (scope, message) where:
//   message.Header.Sender - the sender name the server used; this is how you
//                           route between different server messages.
//   message.Body          - a JSON STRING. Parse it with Ext.decode(...).
//
// The channel is global: every open page receives every message. Two filters
// are mandatory in practice:
//   1. Check message.Header.Sender.
//   2. Check the payload targets THIS user and THIS record. The convention in
//      this codebase is to put the contact id in the payload and compare with
//      Terrasoft.SysValue.CURRENT_USER_CONTACT.value.
//
// Because the handler is invoked outside the view model scope, pass the scope
// explicitly and keep a module-level reference if the handler must survive
// re-initialisation.
//
// Related: Backend/C#/HowToPostMessageToFrontend.cs shows the server half.

define("QSMyEntity1Page", [], function() {

	var currentModule = null;

	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			init: function() {
				this.callParent(arguments);
				currentModule = this;
				Terrasoft.ServerChannel.on(Terrasoft.EventName.ON_MESSAGE,
					this.onServerMessageReceived, currentModule);
			},

			onServerMessageReceived: function(scope, message) {
				var sender = message && message.Header && message.Header.Sender;
				var currentRecordId = this.get("Id");

				if (sender === "SuccessCancelOfOrder") {
					var data = Ext.decode(message.Body);

					// Only react to messages addressed to the current user.
					if (data.currentContactId !== Terrasoft.SysValue.CURRENT_USER_CONTACT.value) {
						return;
					}
					this.showInformationDialog(data.message);
					this.reloadEntity();
					return;
				}

				if (sender === "OrderStatusChanged") {
					var payload = Ext.decode(message.Body);
					if (payload.orderId !== currentRecordId) {
						return;
					}
					if (payload.isError) {
						this.showInformationDialog(payload.message);
					} else {
						this.set("QSStatus", {
							value: payload.statusId,
							displayValue: payload.statusCaption
						});
					}
				}
			},

			// Detach the global listener when the page goes away, otherwise the
			// handler keeps firing against a disposed view model.
			destroy: function() {
				Terrasoft.ServerChannel.un(Terrasoft.EventName.ON_MESSAGE,
					this.onServerMessageReceived, currentModule);
				this.callParent(arguments);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
