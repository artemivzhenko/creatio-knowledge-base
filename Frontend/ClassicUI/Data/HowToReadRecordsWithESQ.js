// --- How to read records with EntitySchemaQuery ------------------------------
// EntitySchemaQuery (ESQ) is the client-side read API. It is asynchronous and
// callback-based; there is no promise wrapper in Classic UI.
//
//   var esq = Ext.create("Terrasoft.EntitySchemaQuery", { rootSchemaName: "X" });
//   esq.addColumn("ColumnName");
//   esq.addColumn("Lookup.Name", "LookupName");   // joined column with an alias
//   esq.filters.add("Key", <filter>);             // see HowToFilterESQ.js
//   esq.getEntityCollection(function(result) { ... }, this);
//
// The callback receives a result object:
//   result.success              - false when the request failed
//   result.errorInfo.message    - the error text
//   result.collection           - Terrasoft.Collection of row view models
//   result.collection.getItems()   -> array
//   result.collection.getCount()   -> number
//   result.collection.each(fn)     -> iterate
//
// Reading a row: item.get("<alias or column name>"). A lookup column read
// without an alias comes back as { value, displayValue }; a column read via a
// join alias ("QSDocumentType.Name" as "DocumentTypeName") comes back as a
// plain string, which is usually what you want for display.
//
// Always pass `this` as the second argument of getEntityCollection so the
// callback keeps the view model scope. Always check result.success before
// touching result.collection.
//
// Single record by id: esq.getEntity(recordId, callback, scope) - convenient
// when you already know the primary key.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Read one record and its joined captions.
			loadShipmentInfo: function() {
				var self = this;
				var recordId = this.get("Id");

				if (!recordId) {
					this.showInformationDialog(this.get("Resources.Strings.SaveRecordFirstMessage"));
					return;
				}

				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSNotice"
				});

				esq.addColumn("QSInformationArrivalService");
				esq.addColumn("QSNumberSeats");
				esq.addColumn("QSDateArrivalEUWarehouse");
				// Joined columns: path + alias.
				esq.addColumn("QSDocumentType.Name", "DocumentTypeName");
				esq.addColumn("QSNatureCargo.Name", "NatureCargoName");

				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "Id", recordId));

				esq.getEntityCollection(function(result) {
					if (!result.success) {
						self.showInformationDialog(result.errorInfo.message);
						return;
					}
					var items = result.collection.getItems();
					if (!items.length) {
						self.showInformationDialog(self.get("Resources.Strings.NoDataFoundMessage"));
						return;
					}
					var record = items[0];
					// Aliased join column -> plain string.
					var documentType = record.get("DocumentTypeName") || "";
					// Direct lookup column -> object.
					var service = record.get("QSInformationArrivalService");

					self.set("QSShipmentInfoText",
						"Document type: " + documentType + "\n" +
						"Service: " + (service ? service.displayValue : ""));
				}, this);
			},

			// Count related records; a common gate before allowing an action.
			countServicesInOrder: function(callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("Id");
				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));

				esq.getEntityCollection(function(result) {
					callback.call(this, result.success ? result.collection.getCount() : 0);
				}, this);
			},

			// Iterate with each().
			collectServiceIds: function(callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("QSService");
				esq.addColumn("QSState");
				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));

				esq.getEntityCollection(function(result) {
					var ids = [];
					if (result.success) {
						result.collection.each(function(item) {
							var service = item.get("QSService");
							if (service) {
								ids.push(service.value);
							}
						});
					}
					callback.call(this, ids);
				}, this);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
