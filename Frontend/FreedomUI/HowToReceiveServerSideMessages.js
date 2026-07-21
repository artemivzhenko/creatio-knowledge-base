define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		// Attribute just holds a reference to the handler function so the exact
		// same reference can be passed to both .on() and .un() below.
		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					"ServerMessageReceivedFunc": {}
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		// --- How to receive a message sent from server-side code --------------
		// Lets a Freedom UI page react to messages pushed from the backend -
		// e.g. a business process script task, an entity subprocess, or a
		// custom web service calling something like
		// ServerMessageManager.SendMessage(...)/PostMessageToUsers.
		//
		// Terrasoft.ServerChannel + Terrasoft.EventName.ON_MESSAGE is the
		// client-side receiving end of that channel.
		//
		// Register the listener on init, always unregister it on destroy -
		// otherwise every page open adds another duplicate listener.
		//
		// The handler MUST be a plain named function, not an arrow function:
		// the third argument to .on()/.un() is the "context" object bound to
		// `this` inside the handler, which only works with a regular function.
		//
		// message.Header.Sender identifies who/what sent the message - always
		// check it so this page only reacts to messages meant for it.
		//
		// Version note: since 8.0.6, HandleViewModelDestroyRequest no longer
		// fires on simple navigation away from the page - use
		// HandleViewModelPauseRequest/HandleViewModelResumeRequest instead if
		// the page can be paused/resumed rather than fully destroyed.

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "crt.HandleViewModelInitRequest",
				handler: async (request, next) => {
					request.$context.ServerMessageReceivedFunc = async function(event, message) {
						if (message.Header.Sender === "SomeMessageId") {
							// Handle the message here - `this` is request.$context
						}
					};

					Terrasoft.ServerChannel.on(
						Terrasoft.EventName.ON_MESSAGE,
						(await request.$context.ServerMessageReceivedFunc),
						request.$context
					);

					return next?.handle(request);
				}
			},
			{
				request: "crt.HandleViewModelDestroyRequest",
				handler: async (request, next) => {
					Terrasoft.ServerChannel.un(
						Terrasoft.EventName.ON_MESSAGE,
						(await request.$context.ServerMessageReceivedFunc),
						request.$context
					);

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
