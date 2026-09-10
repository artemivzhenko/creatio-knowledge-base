define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to attach and release global listeners (pause / resume) -------
		// A Freedom UI page view model is not destroyed when the user navigates
		// away - it is PAUSED and later RESUMED. Anything attached outside the
		// view model (a server channel listener, a DOM listener, a timer) keeps
		// running while the page is paused, firing against a page nobody sees.
		//
		// The pair of lifecycle requests exists exactly for this:
		//
		//   crt.HandleViewModelResumeRequest  the page became active again -
		//                                     attach the listener here
		//   crt.HandleViewModelPauseRequest   the page is being suspended -
		//                                     detach it here
		//
		// Use these INSTEAD of attaching in crt.HandleViewModelInitRequest when
		// the subscription is global. Init runs once; resume/pause run on every
		// visit, which is what keeps the listener count at one.
		//
		// KEEPING THE SAME FUNCTION REFERENCE. .un() only removes a listener when
		// it is handed the very same function object that .on() received. An
		// arrow function created inside each handler is a NEW object every time,
		// so it can never be removed. Store the function in a view model
		// attribute and read it back on pause - that is what the code below does.
		//
		// The attribute must be declared in viewModelConfigDiff, and it is read
		// with `await` like any other attribute.
		//
		// Related: HowToReceiveServerSideMessages.js covers the message payload
		// itself; this file is about the attach/release discipline.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {
					// Holds the handler reference so pause can remove it.
					"ServerMessageReceivedFunc": {}
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[

			// The page became active: build the handler, store it, subscribe.
			{
				request: "crt.HandleViewModelResumeRequest",
				handler: async (request, next) => {

					request.$context.ServerMessageReceivedFunc = async function(event, message) {
						if (message.Header.Sender === "SuVkursiSyncStarted") {
							await request.$context.executeRequest({
								type: "crt.ShowDialogRequest",
								$context: request.$context,
								message: await request.$context.Resources.Strings.SuImportStartMsg,
								actions: [{ key: "OK", config: { color: "primary", caption: "OK" } }]
							});
						}
					};

					Terrasoft.ServerChannel.on(
						Terrasoft.EventName.ON_MESSAGE,
						(await request.$context.ServerMessageReceivedFunc),
						request.$context);

					return next?.handle(request);
				}
			},

			// The page is suspended: remove the SAME reference.
			{
				request: "crt.HandleViewModelPauseRequest",
				handler: async (request, next) => {

					Terrasoft.ServerChannel.un(
						Terrasoft.EventName.ON_MESSAGE,
						(await request.$context.ServerMessageReceivedFunc),
						request.$context);

					return next?.handle(request);
				}
			},

			// Same discipline for a timer.
			{
				request: "crt.HandleViewModelResumeRequest",
				handler: async (request, next) => {
					request.$context.RefreshTimerId = setInterval(async () => {
						await request.$context.executeRequest({
							type: "crt.LoadDataRequest",
							$context: request.$context,
							dataSourceName: "PDS"
						});
					}, 60000);
					return next?.handle(request);
				}
			},
			{
				request: "crt.HandleViewModelPauseRequest",
				handler: async (request, next) => {
					const timerId = await request.$context.RefreshTimerId;
					if (timerId) {
						clearInterval(timerId);
						request.$context.RefreshTimerId = null;
					}
					return next?.handle(request);
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});
