// --- How to call a custom web service from a Classic UI schema ---------------
// Note that many Classic UI pages never call a configuration service at all -
// a business process or an ESQ is often the shorter path to the same result.
// Reach for a service when you need server logic that is neither.
//
// Add "ServiceHelper" to the schema dependencies and call:
//
//   ServiceHelper.callService({
//       serviceName: "<ConfigurationServiceName>",   // the C# class name
//       methodName:  "<OperationName>",              // the [OperationContract]
//       data:        { param1: value1 },             // request body, optional
//       callback:    function(response) { ... },
//       scope:       this
//   });
//
// Response shape: a service method named `GetPartnerDiscount` returns its
// payload under the key "GetPartnerDiscountResult". That is the standard
// Creatio wrapping, so read response[methodName + "Result"].
//
// The request goes to /0/rest/<serviceName>/<methodName>. The service must be a
// configuration service (BaseService descendant) with UserType.SSP or .General
// access declared - see Backend/C#/API/HowToCreateCustomWebService.cs.
//
// callService is asynchronous and has no built-in error branch: a failed call
// simply never reaches the callback, or reaches it with an empty payload. Show
// the body mask before the call and hide it in the callback, and guard against
// an undefined result.
//
// Alternative without ServiceHelper: Terrasoft.AjaxProvider.request({ url, ... })
// for a raw HTTP call. Prefer ServiceHelper - it handles the CSRF header and
// the base URL for you.

define("UsrMyEntity1Page", ["ServiceHelper"], function(ServiceHelper) {
	return {
		entitySchemaName: "UsrMyEntity",
		methods: {

			// Call with a payload and write the answer back into a column.
			loadPartnerDiscount: function() {
				var self = this;
				var parentAccount = this.get("UsrParentAccount");

				if (!parentAccount || !parentAccount.value) {
					return;
				}
				Terrasoft.MaskHelper.ShowBodyMask();

				ServiceHelper.callService({
					serviceName: "UsrMyService",
					methodName: "GetPartnerDiscount",
					data: {
						accountId: parentAccount.value
					},
					callback: function(response) {
						Terrasoft.MaskHelper.HideBodyMask();

						var discount = response && response.GetPartnerDiscountResult;
						if (discount == null) {
							self.showInformationDialog(
								self.get("Resources.Strings.ServiceCallFailedMessage"));
							return;
						}
						self.set("UsrDiscount", discount);
					},
					scope: this
				});
			},

			// Call with no payload; the service creates a record and returns its id.
			createRelatedRecord: function(methodName) {
				var self = this;

				ServiceHelper.callService({
					serviceName: "UsrMyService",
					methodName: methodName,
					callback: function(response) {
						var newId = response && response[methodName + "Result"];
						if (!newId) {
							return;
						}
						console.log("created record", newId);
					},
					scope: this
				});
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
