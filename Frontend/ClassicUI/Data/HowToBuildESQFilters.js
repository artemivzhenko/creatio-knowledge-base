// --- How to build ESQ filters (AND / OR groups, IN, null checks) -------------
// Every ESQ has a root FilterGroup at esq.filters. Two ways to add:
//
//   esq.filters.addItem(filter)        - append without a key
//   esq.filters.add("Key", filter)     - append with a key; reusing the key
//                                        REPLACES the previous filter, so keys
//                                        must be unique (loops append an index)
//
// Creating a single condition - two equivalent factories:
//   esq.createColumnFilterWithParameter(comparison, columnPath, value)
//   Terrasoft.createColumnFilterWithParameter(comparison, columnPath, value)
// The esq.* form is preferred inside a query; the Terrasoft.* form is used when
// you build a filter outside a query (lookupListConfig, detail filters).
//
// Nested groups:
//   var group = Terrasoft.createFilterGroup();          // or Ext.create("Terrasoft.FilterGroup")
//   group.logicalOperation = Terrasoft.LogicalOperatorType.OR;   // or AND
//   group.add("A", ...); group.add("B", ...);
//   esq.filters.addItem(group);
//
// The root group defaults to AND. Setting logicalOperation on the ROOT changes
// how top-level items combine - do not set it to OR unless you mean it, because
// it also loosens the record-scoping filter you added.
//
// Comparison types: EQUAL, NOT_EQUAL, LESS, LESS_OR_EQUAL, GREATER,
// GREATER_OR_EQUAL, IS_NULL, IS_NOT_NULL, CONTAIN, NOT_CONTAIN, START_WITH,
// END_WITH, BETWEEN.
//
// Column paths traverse references with a dot: "QSService.QSProductType".
//
// IN-list: createColumnInFilterWithParameters(columnPath, [v1, v2, ...]) is
// shorter than an OR group when you only need equality against a list.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// AND at the root + a nested OR group.
			findFreightServices: function(callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("Id");

				// Root group: everything below is combined with AND.
				var topFilter = esq.filters;
				topFilter.logicalOperation = Terrasoft.LogicalOperatorType.AND;

				// Condition 1: belongs to this order.
				topFilter.addItem(esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));

				// Condition 2: the service is one of several - a nested OR group.
				var serviceGroup = Terrasoft.createFilterGroup();
				serviceGroup.logicalOperation = Terrasoft.LogicalOperatorType.OR;

				var freightServiceIds = [
					"dd119762-6749-4423-bc61-d513b9302d95",
					"fea0db93-3db3-4c03-a763-a4c593a3aa39",
					"09baaa37-472f-456c-b40d-21f833dc40de"
				];
				freightServiceIds.forEach(function(guid, index) {
					serviceGroup.add("Service" + index, esq.createColumnFilterWithParameter(
						Terrasoft.ComparisonType.EQUAL, "QSService", guid));
				});
				topFilter.addItem(serviceGroup);

				esq.getEntityCollection(function(result) {
					callback.call(this, result.success && result.collection.getCount() > 0);
				}, this);
			},

			// The same list expressed as an IN filter.
			findFreightServicesShorter: function(callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("Id");
				esq.filters.add("Order", esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSOrder", this.get("Id")));
				esq.filters.add("Services", esq.createColumnInFilterWithParameters(
					"QSService", [
						"dd119762-6749-4423-bc61-d513b9302d95",
						"fea0db93-3db3-4c03-a763-a4c593a3aa39"
					]));

				esq.getEntityCollection(function(result) {
					callback.call(this, result.success && result.collection.getCount() > 0);
				}, this);
			},

			// Null checks and a traversed column path.
			findUnassignedByProductType: function(productTypeId, callback) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("Id");
				esq.addColumn("QSService.Name", "ServiceName");

				// Traversed path.
				esq.filters.add("ProductType", esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "QSService.QSProductType", productTypeId));

				// IS NULL takes no value argument.
				esq.filters.add("NoOwner", esq.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.IS_NULL, "QSOwner"));

				esq.getEntityCollection(function(result) {
					callback.call(this, result.success ? result.collection.getItems() : []);
				}, this);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
