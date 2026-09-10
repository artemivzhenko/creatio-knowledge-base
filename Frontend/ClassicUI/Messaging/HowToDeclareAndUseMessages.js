// --- How to declare and use sandbox messages ---------------------------------
// Modules (page, detail, section, embedded module) are isolated. They talk to
// each other through the sandbox, and every message must be DECLARED in the
// `messages` section of BOTH sides.
//
//   messages: {
//       "MessageName": {
//           mode:      Terrasoft.MessageMode.PTP,        // or BROADCAST
//           direction: Terrasoft.MessageDirectionType.PUBLISH   // or SUBSCRIBE
//       }
//   }
//
// mode:
//   PTP        point-to-point. Exactly one subscriber. publish() RETURNS the
//              value the subscriber returned - this is how a detail pulls data
//              from its page synchronously.
//   BROADCAST  every subscriber receives it; publish() returns nothing useful.
//
// direction: declare PUBLISH on the sender and SUBSCRIBE on the receiver. The
// same message name therefore appears in two schemas with opposite directions.
//
// API:
//   this.sandbox.publish("Name", data, tags)
//   this.sandbox.subscribe("Name", handler, scope, tags)
//
// `tags` is an array of strings that narrows delivery. Both sides must use the
// SAME tag. Without tags, a message reaches every module that subscribed to that
// name - including the copy of the page opened in another tab of the same
// workspace, which is a common source of cross-talk.
//
// this.sandbox.id is the unique id of the current module instance. A detail
// publishes with [this.sandbox.id] so the answer is scoped to that instance.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",

		messages: {
			/**
			 * @message DashboardReloaded
			 * Broadcast by the dashboard module after it refreshes.
			 */
			"DashboardReloaded": {
				"mode": Terrasoft.MessageMode.BROADCAST,
				"direction": Terrasoft.MessageDirectionType.SUBSCRIBE
			},
			"FactoriesReload": {
				"mode": Terrasoft.MessageMode.BROADCAST,
				"direction": Terrasoft.MessageDirectionType.PUBLISH
			},
			"QSDocumentTypeChange": {
				"mode": Terrasoft.MessageMode.PTP,
				"direction": Terrasoft.MessageDirectionType.SUBSCRIBE
			},
			"OrderFilesSaveChange": {
				"mode": Terrasoft.MessageMode.PTP,
				"direction": Terrasoft.MessageDirectionType.PUBLISH
			}
		},

		methods: {

			init: function() {
				this.callParent(arguments);

				// Untagged broadcast subscription.
				this.sandbox.subscribe("DashboardReloaded", this.onDashboardReloaded, this);

				// Tagged PTP subscription: only the module publishing with the
				// same tag reaches this handler.
				this.sandbox.subscribe("QSDocumentTypeChange", this.onDocumentTypeChange,
					this, ["order-file"]);
			},

			onDashboardReloaded: function() {
				this.reloadEntity();
			},

			onDocumentTypeChange: function() {
				// Mark the record dirty so the Save button becomes active.
				this.set("IsChanged", true);
			},

			save: function() {
				this.callParent(arguments);
				// Tell the file detail that the page was saved.
				this.sandbox.publish("OrderFilesSaveChange", null, ["order-file"]);
			},

			notifyFactoriesChanged: function() {
				this.sandbox.publish("FactoriesReload");
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
