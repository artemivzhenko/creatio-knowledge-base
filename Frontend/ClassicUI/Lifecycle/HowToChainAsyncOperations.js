// --- How to sequence asynchronous operations (Terrasoft.chain) ---------------
// Classic UI has no promises in the schema API: ESQ, batch queries and process
// starts are all callback-based. Terrasoft.chain runs a list of steps in order,
// handing each one a `next` continuation:
//
//   Terrasoft.chain(
//       function(next) { doStepOne(function() { next(); }, this); },
//       function(next) { doStepTwo(function() { next(); }, this); },
//       function()     { allDone(); },
//       this);                       // scope for every step
//
// Values can be passed forward: next(value) delivers `value` as the SECOND
// argument of the following step, after its own `next`:
//
//   function(next) { next(true); },
//   function(next, flag) { /* flag === true */ }
//
// Not calling next() ends the chain. That is the idiomatic way to abort: a
// failed check shows a dialog and simply returns without continuing.
//
// Terrasoft.each is the matching iteration helper for collections.
//
// Alternative for parallel work: fire the queries independently and count the
// completions yourself, or pack them into one Terrasoft.BatchQuery, which is
// both faster and simpler than a chain of separate reads.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Sequential gates before a status change.
			moveToInWork: function() {
				var self = this;

				Terrasoft.chain(
					// Step 1: the order must have at least one factory record.
					function(next) {
						this.hasFactoryRecords(function(hasRecords) {
							if (!hasRecords) {
								self.showInformationDialog(
									self.get("Resources.Strings.FactoryRequiredMessage"));
								return;   // no next() -> the chain stops here
							}
							next();
						});
					},
					// Step 2: read the service and pass it forward.
					function(next) {
						this.loadPrimaryService(function(service) {
							next(service);
						});
					},
					// Step 3: consume the value produced by step 2.
					function(next, service) {
						if (!service) {
							self.showInformationDialog(
								self.get("Resources.Strings.ServiceRequiredMessage"));
							return;
						}
						self.set("QSPrimaryService", service);
						next();
					},
					// Final step: no `next` parameter needed.
					function() {
						self.save();
					},
					this);
			},

			hasFactoryRecords: function(callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSFactoryDetail"
				});
				esq.addColumn("Id");
				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSQSOrder", this.get("Id")));

				esq.getEntityCollection(function(result) {
					callback.call(this, result.success && result.collection.getCount() > 0);
				}, this);
			},

			loadPrimaryService: function(callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("QSService");
				esq.filters.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));

				esq.getEntityCollection(function(result) {
					var items = result.success ? result.collection.getItems() : [];
					callback.call(this, items.length ? items[0].get("QSService") : null);
				}, this);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
