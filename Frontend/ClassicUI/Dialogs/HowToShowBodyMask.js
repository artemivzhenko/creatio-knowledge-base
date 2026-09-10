// --- How to block the UI while an async operation runs (body mask) -----------
// Terrasoft.MaskHelper draws the "loading" overlay over the whole page:
//
//   Terrasoft.MaskHelper.ShowBodyMask();
//   Terrasoft.MaskHelper.HideBodyMask();
//
// Rules that matter:
//   1. Every ShowBodyMask must have a HideBodyMask on EVERY exit path - the
//      success branch, the error branch, and the early return. A leaked mask
//      locks the page and the user has to reload.
//   2. Hide the mask BEFORE showing a dialog, otherwise the dialog is rendered
//      behind a greyed-out page.
//   3. Nested masks do not stack: a second Show is a no-op and the first Hide
//      removes the overlay. Do not rely on pairing across nested async calls;
//      keep one mask per user-visible operation.
//
// Use it for: batch writes, business process starts the user waits for, service
// calls, multi-step validation chains. Do not use it for a fast ESQ that only
// refreshes a hidden flag.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			loadServicesAndShowWindow: function() {
				var self = this;
				Terrasoft.MaskHelper.ShowBodyMask();

				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("Id");
				esq.addColumn("QSService.Name", "ServiceName");
				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));

				esq.getEntityCollection(function(result) {
					// Hide first, so any dialog below is visible.
					Terrasoft.MaskHelper.HideBodyMask();

					if (!result.success) {
						self.showConfirmationDialog(result.errorInfo.message, function() {}, ["Ok"]);
						return;
					}
					var items = result.collection.getItems();
					if (!items.length) {
						self.showInformationDialog(self.get("Resources.Strings.NoDataFoundMessage"));
						return;
					}
					self.renderServicesWindow(items);
				}, this);
			},

			// Batch write with the mask released on both branches.
			saveChanges: function(changes) {
				var self = this;

				if (!changes.length) {
					// Early return: nothing was shown, nothing to hide.
					return;
				}
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
					}
				}, this);
			},

			renderServicesWindow: function(items) {}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
