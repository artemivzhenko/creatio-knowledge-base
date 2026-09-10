// --- How to read the rows of a detail and reload it --------------------------
// Inside a detail schema the loaded rows are available through getGridData():
//
//   this.getGridData()                  - Terrasoft.Collection of row view models
//   this.getGridData().collection       - the underlying collection
//   this.getGridData().collection.items - plain array of row view models
//   collection.find(fn) / findBy(fn)    - locate a row
//   collection.each(fn)                 - iterate
//   collection.getCount()               - number of loaded rows
//
// Each ITEM is a view model, so read its columns with item.get("Column") and
// write with item.set("Column", value) - same value shapes as on a page
// (lookups are { value, displayValue }).
//
// Caution: getGridData() returns only the rows currently LOADED into the grid.
// With paging enabled that is not the whole detail. If you need all rows, query
// the entity with an EntitySchemaQuery instead (see Data/).
//
// Reloading:
//   this.reloadGridData()   - re-fetch the detail rows (inside the detail).
//   this.updateDetail({ detail: "<DetailKey>" })  - from the PAGE, refresh one
//                                                   detail by its `details` key.
//   this.reloadEntity()     - from the PAGE, reload the record and everything.
//
// Writing changes back: setting item.set(...) updates the UI only. Persist with
// an UpdateQuery / BatchQuery (see Data/HowToUpdateRecords.js) or by saving the
// row through the grid.

define("QSMyDetail", [], function() {
	return {
		entitySchemaName: "QSOrderFile",

		methods: {

			// Find a loaded row by id.
			findRowById: function(recordId) {
				return this.getGridData().collection.find(function(item) {
					return item.get("Id") === recordId;
				});
			},

			// Detect a duplicate before allowing a value.
			hasRowWithDocumentType: function(documentTypeId) {
				return !!this.getGridData().collection.findBy(function(item) {
					var type = item.get("QSDocumentType");
					return !!type && type.value === documentTypeId;
				});
			},

			// Collect the rows the user touched, then persist them in one batch.
			collectChangedRows: function() {
				var changed = [];
				this.getGridData().collection.items.forEach(function(item) {
					if (item.isUpdated) {
						changed.push({
							Id: item.get("Id"),
							documentTypeId: item.get("QSDocumentType").value
						});
						item.isUpdated = false;
					}
				});
				return changed;
			},

			// Write a value into a row and mark it for the batch above.
			setRowDocumentType: function(item, documentTypeId, caption) {
				item.set("QSDocumentType", { value: documentTypeId, displayValue: caption });
				item.isUpdated = true;
			},

			refresh: function() {
				this.reloadGridData();
			}
		}
	};
});

// --- From the PAGE side ------------------------------------------------------
// define("QSMyEntity1Page", [], function() {
//     return {
//         entitySchemaName: "QSMyEntity",
//         methods: {
//             refreshServicesDetail: function() {
//                 // The argument is the KEY from the page `details` object.
//                 this.updateDetail({ detail: "QSSchema2d707869Detailacdf157e" });
//             },
//             refreshEverything: function() {
//                 this.reloadEntity();
//             }
//         }
//     };
// });
