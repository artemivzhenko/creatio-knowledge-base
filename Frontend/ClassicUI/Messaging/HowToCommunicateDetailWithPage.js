// --- How a detail exchanges data with its page -------------------------------
// A detail cannot call this.get("SomeColumn") for a PAGE column: it is a
// separate module with its own view model. The Classic UI pattern is a pair of
// PTP messages:
//
//   Detail -> Page   "GetColumnsValues"  request; the page RETURNS the values,
//                    so sandbox.publish() gives them back synchronously.
//   Page  -> Detail  "SetDetailButtonState" push; the page tells the detail to
//                    change state.
//
// PTP publish returns whatever the subscriber returned. That is the whole trick:
//
//   var data = this.sandbox.publish("GetColumnsValues",
//       ["QSService", "QSOrder"], [this.sandbox.id]);
//   var serviceId = data.QSService?.value;
//
// Timing. The detail is constructed before the page has finished subscribing,
// so a publish issued directly in the detail's init can return undefined. The
// codebase defers the first exchange with a short setTimeout and always guards
// for a null answer. Guard, do not assume.
//
// Lifetime. Both sides must unsubscribe or check this.destroyed before touching
// the view model: a detail can outlive a page transition and then writes into a
// disposed model.

// ============================ DETAIL SIDE ====================================
define("QSMyDetail", [], function() {
	return {
		entitySchemaName: "QSAdditionalServices",

		messages: {
			"GetColumnsValues":     { mode: Terrasoft.MessageMode.PTP,
									  direction: Terrasoft.MessageDirectionType.PUBLISH },
			"UpdateParentFields":   { mode: Terrasoft.MessageMode.PTP,
									  direction: Terrasoft.MessageDirectionType.PUBLISH },
			"SetDetailButtonState": { mode: Terrasoft.MessageMode.PTP,
									  direction: Terrasoft.MessageDirectionType.SUBSCRIBE }
		},

		methods: {

			init: function() {
				this.callParent(arguments);
				setTimeout(function() {
					this.sandbox.subscribe("SetDetailButtonState", this.onSetButtonState, this);
					this.readParentColumns();
				}.bind(this), 50);
			},

			// Pull page columns. Note the tag: [this.sandbox.id].
			readParentColumns: function() {
				var parentData = this.sandbox.publish(
					"GetColumnsValues",
					["QSService", "QSOrder", "QSStatus"],
					[this.sandbox.id]);

				if (!parentData) {
					console.warn("QSMyDetail: page did not answer GetColumnsValues");
					return null;
				}
				return parentData;
			},

			// Push a value INTO the page.
			pushValueToParent: function() {
				this.sandbox.publish("UpdateParentFields",
					{ QSTotalAmount: 1250.5 },
					["QSMyEntity1Page_UpdateParentFields"]);
			},

			onSetButtonState: function(state) {
				if (this.destroyed) {
					return;
				}
				this.set("IsAddButtonEnabled", !!state.enabled);
			}
		}
	};
});

// ============================= PAGE SIDE =====================================
// define("QSMyEntity1Page", [], function() {
//     return {
//         entitySchemaName: "QSMyEntity",
//         messages: {
//             "GetColumnsValues":     { mode: Terrasoft.MessageMode.PTP,
//                                       direction: Terrasoft.MessageDirectionType.SUBSCRIBE },
//             "UpdateParentFields":   { mode: Terrasoft.MessageMode.PTP,
//                                       direction: Terrasoft.MessageDirectionType.SUBSCRIBE },
//             "SetDetailButtonState": { mode: Terrasoft.MessageMode.PTP,
//                                       direction: Terrasoft.MessageDirectionType.PUBLISH }
//         },
//         methods: {
//             init: function() {
//                 this.callParent(arguments);
//                 this.sandbox.subscribe("GetColumnsValues", this.onGetColumnsValues, this);
//                 this.sandbox.subscribe("UpdateParentFields", this.onUpdateParentFields,
//                     this, ["QSMyEntity1Page_UpdateParentFields"]);
//             },
//
//             // The RETURN value is what the detail receives.
//             onGetColumnsValues: function(columnNames) {
//                 var result = {};
//                 (columnNames || []).forEach(function(name) {
//                     result[name] = this.get(name);
//                 }, this);
//                 return result;
//             },
//
//             onUpdateParentFields: function(values) {
//                 Object.keys(values).forEach(function(name) {
//                     this.set(name, values[name]);
//                 }, this);
//                 this.set("IsChanged", true);
//             },
//
//             blockDetailButton: function(message) {
//                 if (this.destroyed) { return; }
//                 this.sandbox.publish("SetDetailButtonState",
//                     { enabled: false, message: message });
//             }
//         }
//     };
// });
