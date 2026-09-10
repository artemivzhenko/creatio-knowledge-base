// --- How to control the "add record" button of a detail ----------------------
// The stock button is named "AddRecordButton". Merge it in the detail diff and
// bind visible / enabled to virtual attributes, then override addRecord() to
// gate the action itself.
//
// Why both? The bindings grey the button out, but a disabled button gives the
// user no reason. Overriding addRecord lets you explain why the action is
// blocked, and it also covers the keyboard / API paths that bypass the button.
//
// addRecord() is the base method that creates a new detail record. If you
// override it you MUST call this.callParent(arguments) on every path that
// should proceed, otherwise adding rows stops working.
//
// A detail lives in its own sandbox module, so it cannot read the page columns
// directly. To decide whether adding is allowed it asks the page over the
// sandbox - see Messaging/HowToCommunicateDetailWithPage.js.

define("QSMyDetail", [], function() {
	return {
		entitySchemaName: "QSAdditionalServices",

		messages: {
			// Detail -> page request for column values.
			"GetColumnsValues": {
				mode: Terrasoft.MessageMode.PTP,
				direction: Terrasoft.MessageDirectionType.PUBLISH
			},
			// Page -> detail push of the button state.
			"SetDetailButtonState": {
				mode: Terrasoft.MessageMode.PTP,
				direction: Terrasoft.MessageDirectionType.SUBSCRIBE
			}
		},

		attributes: {
			"IsAddButtonVisible": {
				dataValueType: Terrasoft.DataValueType.BOOLEAN, value: true
			},
			"IsAddButtonEnabled": {
				dataValueType: Terrasoft.DataValueType.BOOLEAN, value: true
			},
			"ButtonBlockMessage": {
				dataValueType: Terrasoft.DataValueType.TEXT, value: ""
			}
		},

		diff: [
			{
				operation: "merge",
				name: "AddRecordButton",
				values: {
					visible: { bindTo: "IsAddButtonVisible" },
					enabled: { bindTo: "IsAddButtonEnabled" }
				}
			}
		],

		methods: {

			init: function() {
				this.callParent(arguments);

				// The detail is created before the page finishes wiring its own
				// subscriptions; a short defer avoids a race on first render.
				setTimeout(function() {
					try {
						this.sandbox.subscribe("SetDetailButtonState", this.onSetButtonState, this);
						this.checkButtonStateOnInit();
					} catch (e) {
						console.error("QSMyDetail: init failed:", e);
					}
				}.bind(this), 50);
			},

			// Page pushes { enabled, message } to the detail.
			onSetButtonState: function(state) {
				this.set("IsAddButtonEnabled", !!state.enabled);
				this.set("ButtonBlockMessage", state.message || "");
			},

			checkButtonStateOnInit: function() {
				var parentData = this.sandbox.publish(
					"GetColumnsValues", ["QSService", "QSOrder"], [this.sandbox.id]);
				if (!parentData) {
					return;
				}
				this.set("IsAddButtonEnabled", !!parentData.QSService);
			},

			// Gate the action and explain the refusal.
			addRecord: function() {
				if (!this.get("IsAddButtonEnabled")) {
					this.showBlockedMessage();
					return;
				}
				try {
					this.callParent(arguments);
				} catch (e) {
					console.error("QSMyDetail: addRecord failed:", e);
					this.callParent(arguments);
				}
			},

			showBlockedMessage: function() {
				var message = this.get("ButtonBlockMessage");
				this.showInformationDialog(message ||
					this.get("Resources.Strings.CannotAddRecordMessage"));
			}
		}
	};
});
