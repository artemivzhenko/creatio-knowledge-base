// --- How to create, update and delete records from the client ----------------
// Three query classes, all created with Ext.create and all asynchronous:
//
//   Terrasoft.InsertQuery { rootSchemaName }
//   Terrasoft.UpdateQuery { rootSchemaName }   + filters to select the rows
//   Terrasoft.DeleteQuery { rootSchemaName }   + filters to select the rows
//
// Setting values:
//   query.setParameterValue("ColumnName", value, Terrasoft.DataValueType.<TYPE>);
//
// The DataValueType argument is not optional in practice: without it a GUID may
// be sent as text and the server rejects the row. Use GUID for lookups and pass
// the RAW guid, not the { value, displayValue } object.
//
// Selecting rows for update / delete:
//   query.filters.add("IdFilter", Terrasoft.createColumnFilterWithParameter(
//       Terrasoft.ComparisonType.EQUAL, "Id", recordId));
// An UpdateQuery with no filters updates EVERY row of the table. Always filter.
//
// Executing:
//   query.execute(function(response) {
//       response.success, response.errorInfo, response.id (insert)
//   }, this);
//
// These queries bypass the page view model: they do not run page validation and
// do not refresh the UI. After changing data the page is showing, reload it
// (reloadEntity / updateDetail / reloadGridData).

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// INSERT
			logCancelAttempt: function(orderId, callbackData) {
				var insertQuery = Ext.create("Terrasoft.InsertQuery", {
					rootSchemaName: "QSLogOrderCancelTry"
				});

				insertQuery.setParameterValue("QSContact",
					Terrasoft.SysValue.CURRENT_USER_CONTACT.value, Terrasoft.DataValueType.GUID);
				insertQuery.setParameterValue("QSOrder", orderId, Terrasoft.DataValueType.GUID);
				insertQuery.setParameterValue("QSOrderGuidText", orderId.toString(), Terrasoft.DataValueType.TEXT);
				insertQuery.setParameterValue("QSTime", new Date(), Terrasoft.DataValueType.DATE_TIME);
				insertQuery.setParameterValue("QSURLAddress", window.location.href, Terrasoft.DataValueType.TEXT);
				insertQuery.setParameterValue("QSProcessCallback", callbackData, Terrasoft.DataValueType.TEXT);

				insertQuery.execute(function(response) {
					if (response.success) {
						console.log("log record created", response.id);
					} else {
						console.error("insert failed", response.errorInfo);
					}
				}, this);
			},

			// UPDATE
			setServiceState: function(serviceId, stateId) {
				var update = Ext.create("Terrasoft.UpdateQuery", {
					rootSchemaName: "QSServicesInOrder"
				});

				update.setParameterValue("QSState", stateId, Terrasoft.DataValueType.GUID);
				// Never omit the filter on an UpdateQuery.
				update.filters.add("IdFilter", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "Id", serviceId));

				update.execute(function(response) {
					if (!response.success) {
						this.showInformationDialog(response.errorInfo.message);
						return;
					}
					this.updateDetail({ detail: "QSSchema2d707869Detailacdf157e" });
				}, this);
			},

			// DELETE
			removeAccountLink: function(linkId) {
				var deleteQuery = Ext.create("Terrasoft.DeleteQuery", {
					rootSchemaName: "QSOrderAccount"
				});
				deleteQuery.filters.add("IdFilter", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "Id", linkId));

				deleteQuery.execute(function(response) {
					if (!response.success) {
						console.error("delete failed", response.errorInfo);
					}
				}, this);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
