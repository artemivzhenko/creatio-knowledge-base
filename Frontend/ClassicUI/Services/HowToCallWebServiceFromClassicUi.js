// --- How to call a custom web service from a Classic UI schema ---------------
// PROVENANCE: no Classic UI schema in the QubeSoft package calls a configuration
// web service - that package reaches the server through business processes and
// ESQ instead. The ServiceHelper form below is taken from the _SalesUp_Base
// package in the same repository, where it is used against "SuBase_Service".
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
// Response shape: a service method named `GetImporterDiscount` returns its
// payload under the key "GetImporterDiscountResult". That is the standard
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

define("QSMyEntity1Page", ["ServiceHelper"], function(ServiceHelper) {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Call with a payload and write the answer back into a column.
			loadImporterDiscount: function() {
				var self = this;
				var holding = this.get("QSHolding");

				if (!holding || !holding.value) {
					return;
				}
				Terrasoft.MaskHelper.ShowBodyMask();

				ServiceHelper.callService({
					serviceName: "QSBase_Service",
					methodName: "GetImporterDiscount",
					data: {
						holdingId: holding.value
					},
					callback: function(response) {
						Terrasoft.MaskHelper.HideBodyMask();

						var discount = response && response.GetImporterDiscountResult;
						if (discount == null) {
							self.showInformationDialog(
								self.get("Resources.Strings.ServiceCallFailedMessage"));
							return;
						}
						self.set("QSImporterDiscount", discount);
					},
					scope: this
				});
			},

			// Call with no payload; the service creates a record and returns its id.
			createRelatedRecord: function(methodName) {
				var self = this;

				ServiceHelper.callService({
					serviceName: "QSBase_Service",
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
