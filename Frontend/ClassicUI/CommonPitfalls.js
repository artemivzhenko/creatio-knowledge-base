// --- Common Classic UI mistakes and how they show up -------------------------
// Every item below was observed in real schemas in this repository. They fail
// silently, which is what makes them expensive.
//
// 1. TWO `methods:` KEYS IN ONE SCHEMA OBJECT
//    A schema returns a plain object literal, so a second `methods:` key
//    OVERWRITES the first. Every method in the earlier block disappears and the
//    bindings that referenced them do nothing. Same for a duplicated `diff:`.
//    Symptom: a button does nothing, no error in the console.
//    Fix: one block per key. Search the file for `methods:` before adding one.
//
// 2. CALLBACK PASSED OUTSIDE THE executeProcess CONFIG
//    ProcessModuleUtilities.executeProcess takes ONE argument. Writing
//        executeProcess(config, function(response) {...}, this)
//    starts the process and silently drops the function.
//    Symptom: the process runs, the "finished" dialog never appears, the body
//    mask is never hidden and the page stays locked.
//    Fix: put callback and scope INSIDE the config object.
//
// 3. MISSING this.callParent(arguments)
//    An override without it replaces base behaviour instead of extending it.
//    Symptom depends on the method: no data in onEntityInitialized, the record
//    never saving in save(), the grid staying empty in a detail init().
//    Fix: call the parent, first in initialisation methods, last in destroy().
//
// 4. LOOKUP COMPARED AS A SCALAR
//    A lookup column is { value, displayValue } or null - never a plain guid.
//        if (this.get("QSStatus") === StatusInWork)      // always false
//        if (this.get("QSStatus").value === StatusInWork) // throws when empty
//    Fix: this.get("QSStatus")?.value === StatusInWork
//
// 5. LOOKUP WRITTEN WITHOUT displayValue
//    set("QSStatus", { value: id }) stores the value but leaves the control
//    blank until the page reloads.
//    Fix: always pass both keys, or null to clear.
//
// 6. UpdateQuery WITHOUT FILTERS
//    An UpdateQuery with no filter updates EVERY row of the table. There is no
//    confirmation and no undo.
//    Fix: add the Id filter before execute(), always.
//
// 7. BODY MASK LEAKED ON AN ERROR PATH
//    ShowBodyMask() with HideBodyMask() only in the success branch locks the
//    page whenever the query fails.
//    Fix: hide it on every exit path, and hide it BEFORE showing a dialog.
//
// 8. FILTER KEYS REUSED IN A LOOP
//    filters.add("Filter", ...) inside a loop keeps overwriting the same key,
//    so only the last condition survives.
//    Fix: append an index - filters.add("Filter" + i, ...).
//
// 9. DEFERRED CALLBACK TOUCHING A DISPOSED PAGE
//    A setTimeout / ESQ callback can arrive after the user navigated away and
//    then writes into a dead view model.
//    Fix: check this.destroyed, and compare the guid in window.location.hash
//    with this.get("Id") - see Navigation/.
//
// 10. GLOBAL LISTENERS AND OBSERVERS NEVER RELEASED
//     Terrasoft.ServerChannel.on, MutationObserver, document listeners and
//     window.* closures attached in init keep firing for every later page.
//     Fix: release them all in destroy().
//
// 11. ADDING A CONTROL WITHOUT ITS GRID LAYOUT
//     A field inserted straight into a CONTROL_GROUP with no GRID_LAYOUT between
//     them ignores the 24-column layout.
//     Fix: tab -> group (itemType 15) -> grid layout (itemType 0) -> field.
//
// 12. HIDING ONLY ONE MODE OF A SECTION BUTTON
//     Sections render in combined and separate mode with separate elements.
//     Hiding SeparateModeAddRecordButton alone leaves the button visible in the
//     other mode.
//     Fix: handle CombinedModeAddRecordButton too.
//
// 13. filterMethod WITHOUT THE MASTER CONDITION
//     filterMethod REPLACES the automatic master filter of a detail. Omitting
//     the master condition shows every row in the table on every record.
//     Fix: include the detailColumn = master Id condition in the returned group.
//
// 14. getIncrementCode CALLED ON AN EXISTING RECORD
//     Without an isAddMode()/isCopyMode() guard the number is regenerated every
//     time the record is opened.
//
// 15. getGridData() TREATED AS THE WHOLE DETAIL
//     It returns the rows currently LOADED. With paging on that is one page.
//     Fix: query the entity with an ESQ when you need all rows.

define("QSMyEntity1Page", ["ProcessModuleUtilities"], function(ProcessModuleUtilities) {

	const StatusInWork = "f6c25e34-63f3-4b6d-9769-db0f37d42f0e";

	return {
		entitySchemaName: "QSMyEntity",

		// ONE methods block.
		methods: {

			onEntityInitialized: function() {
				this.callParent(arguments);          // 3
				this.applyStatusRules();
			},

			applyStatusRules: function() {
				// 4: optional chaining, no throw on an empty lookup
				var isInWork = this.get("QSStatus")?.value === StatusInWork;
				this.set("QSSellerRequired", isInWork);
			},

			setStatusInWork: function() {
				// 5: both keys
				this.set("QSStatus", { value: StatusInWork, displayValue: "In work" });
			},

			runProcess: function() {
				var self = this;
				Terrasoft.MaskHelper.ShowBodyMask();

				ProcessModuleUtilities.executeProcess({
					sysProcessName: "QSProcess_2da82f9",
					parameters: { orderId: this.get("Id") },
					// 2: callback inside the config
					callback: function(request, success) {
						Terrasoft.MaskHelper.HideBodyMask();   // 7: every path
						if (!success) {
							self.showInformationDialog(
								self.get("Resources.Strings.ProcessFailedMessage"));
							return;
						}
						// 9: the page may be gone by now
						if (self.destroyed) {
							return;
						}
						self.reloadEntity();
					},
					scope: this
				});
			},

			updateService: function(serviceId, stateId) {
				var update = Ext.create("Terrasoft.UpdateQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				update.setParameterValue("QSState", stateId, Terrasoft.DataValueType.GUID);
				// 6: never execute an unfiltered UpdateQuery
				update.filters.add("IdFilter", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "Id", serviceId));
				update.execute(function() {}, this);
			},

			buildRoleFilter: function(esq, roleIds) {
				var group = Terrasoft.createFilterGroup();
				group.logicalOperation = Terrasoft.LogicalOperatorType.OR;
				roleIds.forEach(function(roleId, index) {
					// 8: unique key per iteration
					group.add("RoleFilter" + index,
						Terrasoft.createColumnFilterWithParameter(
							Terrasoft.ComparisonType.EQUAL, "SysRole", roleId));
				});
				return group;
			},

			destroy: function() {
				// 10: release what init attached
				this.callParent(arguments);
			}
		},

		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
