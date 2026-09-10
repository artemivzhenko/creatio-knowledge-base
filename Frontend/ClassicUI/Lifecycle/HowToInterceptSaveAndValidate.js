// --- How to intercept the save pipeline and validate -------------------------
// The save pipeline, in call order:
//
//   save()                       - entry point, also fired by the Save button
//     validate()                 - SYNCHRONOUS validation; return false to stop
//     asyncValidate(cb, scope)   - ASYNCHRONOUS validation; call back with a
//                                  response object to continue or stop
//     saveEntity(cb, scope)      - issues the save request
//     validateSaveEntityResponse(response, cb, scope)
//                                - inspects the server answer
//     onSaved()                  - after a successful save
//
// asyncValidate is the hook to use whenever a check needs a server round trip
// (ESQ, a service call). Its contract:
//   - call this.callParent([wrapperFunction, scope])
//   - inside the wrapper, first check the response from the base validation with
//     this.validateResponse(response); if it is false, stop.
//   - when your own checks pass, call callback.call(scope, response)
//   - to REJECT the save, call back with { success: false, message: "..." }
//
// Chaining several async checks: Terrasoft.chain runs functions in sequence,
// each receiving a `next` continuation. Not calling next() silently aborts the
// save, which is exactly how a failed check stops it.
//
// Overriding save() itself is for side effects (notify a detail, publish a
// message), not for validation. Always call this.callParent(arguments).

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Side effect after the standard save.
			save: function() {
				this.callParent(arguments);
				this.sandbox.publish("OrderFilesSaveChange", null, ["order-file"]);
			},

			// Synchronous check. Returning false stops the save immediately.
			validate: function() {
				var weight = this.get("QSActualWeight");
				if (weight != null && weight <= 0) {
					this.showInformationDialog(
						this.get("Resources.Strings.WeightMustBePositiveMessage"));
					return false;
				}
				return this.callParent(arguments);
			},

			// Asynchronous checks chained one after another.
			asyncValidate: function(callback, scope) {
				this.callParent([function(response) {
					// Base validation failed - stop here.
					if (!this.validateResponse(response)) {
						return;
					}
					Terrasoft.chain(
						function(next) {
							this.validateTrademarkDetail(function(stepResponse) {
								if (this.validateResponse(stepResponse)) {
									next();
								}
							}, this);
						},
						function(next) {
							this.validateContainerFields(function(stepResponse) {
								if (this.validateResponse(stepResponse)) {
									next();
								}
							}, this);
						},
						function() {
							// Every check passed - let the save continue.
							callback.call(scope, response);
						},
						this);
				}, this]);
			},

			// A single async check. Report failure through the response object,
			// never by throwing.
			validateTrademarkDetail: function(callback, scope) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSTrademarkInOrder"
				});
				esq.addColumn("Id");
				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));

				esq.getEntityCollection(function(result) {
					if (result.success && result.collection.getCount() === 0) {
						callback.call(scope, {
							success: false,
							message: this.get("Resources.Strings.TrademarkRequiredMessage")
						});
						return;
					}
					callback.call(scope, { success: true });
				}, this);
			},

			validateContainerFields: function(callback, scope) {
				callback.call(scope, { success: true });
			},

			// Inspect the server answer to the save request.
			validateSaveEntityResponse: function(response, callback, scope) {
				if (response && !response.success) {
					console.error("save failed", response.errorInfo);
				}
				this.callParent(arguments);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
