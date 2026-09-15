// --- How to read and write field values --------------------------------------
// The view model is a key/value store. Everything goes through get / set.
//
//   this.get("ColumnName")          - current value.
//   this.set("ColumnName", value)   - write a value and notify bindings.
//
// Value SHAPE depends on the column type - this is the single most common
// source of bugs in Classic UI:
//
//   TEXT / INTEGER / FLOAT / BOOLEAN / DATE_TIME -> the raw scalar.
//   LOOKUP / ENUM                                -> an object:
//                                                   { value: "<guid>",
//                                                     displayValue: "<caption>" }
//
// So a lookup is never compared directly. Always read `.value`, and guard for
// null because an empty lookup is null, not an object with an empty value.
//
//   var status = this.get("UsrStatus");
//   if (status && status.value === StatusInWork) { ... }
//   // or with optional chaining, which the codebase uses freely:
//   if (this.get("UsrStatus")?.value === StatusInWork) { ... }
//
// Writing a lookup requires BOTH keys. Setting only `value` leaves the control
// blank until the page reloads:
//
//   this.set("UsrStatus", { value: StatusInWork, displayValue: "In work" });
//
// Clearing a lookup: this.set("UsrStatus", null).
//
// Useful built-in columns:
//   "Id"          - primary key of the record (empty until first save).
//   "CardState"   - ConfigurationEnums.CardStateV2.ADD / EDIT / COPY.
//   "IsChanged"   - marks the record dirty so the Save button lights up.

define("UsrMyEntity1Page", [], function() {

	const StatusInWork  = "f6c25e34-63f3-4b6d-9769-db0f37d42f0e";
	const Yes = { value: "c92c530c-027a-48ae-ba5c-93e7dcbed661", displayValue: "Yes" };

	return {
		entitySchemaName: "UsrMyEntity",
		methods: {

			readValues: function() {
				// Scalars.
				var name   = this.get("UsrName");          // string
				var weight = this.get("UsrWeight");  // number
				var isPaid = this.get("UsrIsPaid");        // boolean
				var date   = this.get("UsrMyEntityDate");     // Date

				// Lookups: object or null.
				var status = this.get("UsrStatus");
				var statusId = status ? status.value : null;
				var statusCaption = status ? status.displayValue : "";

				// Record id: empty string / undefined for an unsaved record.
				var recordId = this.get("Id");

				return { name: name, weight: weight, isPaid: isPaid, date: date,
					statusId: statusId, statusCaption: statusCaption, recordId: recordId };
			},

			writeValues: function() {
				// Scalar write.
				this.set("UsrName", "ORD-000123");

				// Lookup write: always pass value AND displayValue.
				this.set("UsrStatus", { value: StatusInWork, displayValue: "In work" });
				this.set("UsrHasDiscount", Yes);

				// Clear a lookup.
				this.set("UsrSalesOwner", null);

				// Mark the record dirty when you changed something the framework
				// cannot see (for example a value pushed from a detail).
				this.set("IsChanged", true);
			},

			// Copy a lookup value from one column to another without losing the
			// caption. Never assign the object by reference if the source may be
			// mutated later - clone it.
			copyLookup: function(fromColumn, toColumn) {
				var source = this.get(fromColumn);
				this.set(toColumn, source
					? { value: source.value, displayValue: source.displayValue }
					: null);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
