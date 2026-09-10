// --- How to send several queries in one request (BatchQuery) -----------------
// Terrasoft.BatchQuery packs Insert / Update / Delete / ESQ queries into a
// single round trip. Use it whenever you would otherwise fire N queries in a
// loop: it is faster and the whole batch reports one success flag.
//
//   var bq = Ext.create("Terrasoft.BatchQuery");
//   bq.add(query1);
//   bq.add(query2);
//   bq.execute(function(response) { ... }, this);
//
// response.success       - false if the batch failed
// response.errorInfo     - error details
// response.queryResults  - array of per-query results, in the order added; for
//                          an ESQ inside the batch read
//                          response.queryResults[i].rows
//
// A batch is NOT a transaction: a partial failure can leave some rows written.
// If atomicity matters, do the work in a business process or a server service.
//
// Pair batches with the body mask so the user sees that something is running -
// see Dialogs/HowToShowBodyMask.js.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Update many rows in one request.
			applyServiceChanges: function(changes) {
				if (!changes.length) {
					return;
				}
				var self = this;
				Terrasoft.MaskHelper.ShowBodyMask();

				var bq = Ext.create("Terrasoft.BatchQuery");

				changes.forEach(function(change) {
					var update = Ext.create("Terrasoft.UpdateQuery", {
						rootSchemaName: "QSServicesInOrder"
					});
					update.setParameterValue(change.field, change.value, change.type);
					update.filters.add("IdFilter", Terrasoft.createColumnFilterWithParameter(
						Terrasoft.ComparisonType.EQUAL, "Id", change.id));
					bq.add(update);
				});

				bq.execute(function(result) {
					Terrasoft.MaskHelper.HideBodyMask();

					if (!result.success) {
						self.showConfirmationDialog(result.errorInfo.message, function() {}, ["Ok"]);
						return;
					}
					self.sandbox.publish("FactoriesReload", null, ["order-factories"]);
				}, this);
			},

			// Replace a set of links: delete the old ones and insert the new ones
			// in a single batch.
			replaceAccountLinks: function(accountIds) {
				var orderId = this.get("Id");
				var bq = Ext.create("Terrasoft.BatchQuery");

				var deleteQuery = Ext.create("Terrasoft.DeleteQuery", {
					rootSchemaName: "QSOrderAccount"
				});
				deleteQuery.filters.add("OrderFilter", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSQSOrder", orderId));
				bq.add(deleteQuery);

				accountIds.forEach(function(accountId) {
					var insertQuery = Ext.create("Terrasoft.InsertQuery", {
						rootSchemaName: "QSOrderAccount"
					});
					insertQuery.setParameterValue("QSAccount", accountId, Terrasoft.DataValueType.GUID);
					insertQuery.setParameterValue("QSQSOrder", orderId, Terrasoft.DataValueType.GUID);
					bq.add(insertQuery);
				});

				bq.execute(function(result) {
					if (!result.success) {
						this.showInformationDialog(result.errorInfo.message);
					}
				}, this);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
