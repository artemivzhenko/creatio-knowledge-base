// --- How to add many records to a detail at once (LookupMultiAddMixin) -------
// Follows the Creatio Academy recipe "Implement the bulk addition of records
// to the detail".
//
// For a many-to-many detail the stock "+" opens an empty edit page, one row at
// a time. Terrasoft.LookupMultiAddMixin replaces that with a multi-select
// lookup window that creates every link row in one go.
//
// WHAT YOU MUST PROVIDE
//   mixins.LookupMultiAddMixin      "Terrasoft.LookupMultiAddMixin"
//   init()                          call the mixin init
//   getMultiSelectLookupConfig()    describes the link table:
//       rootEntitySchemaName    the MASTER entity          ("UsrMyEntity")
//       rootColumnName          link column -> master      ("UsrMyEntity")
//       relatedEntitySchemaName the entity being picked     ("UsrRelatedEntity")
//       relatedColumnName       link column -> picked row   ("UsrRelatedEntity")
//   addRecord()                     override to call openLookupWithMultiSelect(true)
//   getAdditionalLookupFilters()    optional: a FilterGroup narrowing the window
//
// THE UNSAVED-MASTER PROBLEM. The link rows need the master record id, so the
// window cannot open while the master is still in ADD/COPY state. The pattern:
// ask the page for its state (GetCardState), and if it is new, ask it to save
// (SaveRecord) and continue in onCardSaved. See
// BaseMethods/StandardMessagesAndAttributes.js.
//
// POST-CREATE FIX-UP. The mixin only fills the two link columns. Any other
// column of the link table stays empty, so a follow-up UpdateQuery is needed -
// run it from onGridDataLoaded, once the new rows are actually in the grid, and
// scope it with an IS NULL filter so you only touch the fresh rows.

define("UsrSchemae5af2d9bDetail", ["LookupMultiAddMixin", "ConfigurationEnums"],
	function(LookupMultiAddMixin, configurationEnums) {
		return {
			entitySchemaName: "UsrRelatedInMyEntity",
			details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,
			diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/,

			mixins: {
				LookupMultiAddMixin: "Terrasoft.LookupMultiAddMixin"
			},

			methods: {

				init: function() {
					this.callParent(arguments);
					this.mixins.LookupMultiAddMixin.init.call(this);
				},

				getAddRecordButtonVisible: function() {
					return this.getToolsVisible();
				},

				// Entry point for the "+" button.
				addRecord: function() {
					var masterCardState = this.sandbox.publish("GetCardState", null, [this.sandbox.id]);
					var isNewRecord = masterCardState && (
						masterCardState.state === configurationEnums.CardStateV2.ADD ||
						masterCardState.state === configurationEnums.CardStateV2.COPY);

					if (isNewRecord) {
						// Master not saved yet: save it, continue in onCardSaved.
						this.set("UsrPendingAddRecord", true);
						this.sandbox.publish("SaveRecord",
							{ isSilent: true, messageTags: [this.sandbox.id] },
							[this.sandbox.id]);
						return;
					}
					this.proceedToOpenLookup();
				},

				// Fires when the master page finished saving.
				onCardSaved: function() {
					if (this.get("UsrPendingAddRecord")) {
						this.set("UsrPendingAddRecord", false);
						this.proceedToOpenLookup();
					}
				},

				// Read a master column, then open the window.
				proceedToOpenLookup: function() {
					this.getMasterAccountValue(function(accountId) {
						if (!accountId) {
							this.showInformationDialog(
								this.get("Resources.Strings.SpecifyHoldingFirstMessage"));
							return;
						}
						this.set("UsrParentAccountId", accountId);
						this.set("UsrNeedParentFix", true);
						this.openLookupWithMultiSelect(true);
					}, this);
				},

				// esq.getEntity(id, callback, scope) reads a single record by key.
				getMasterAccountValue: function(callback, scope) {
					var masterRecordId = this.getMasterRecordId();
					if (!masterRecordId) {
						callback.call(scope || this, null);
						return;
					}
					var esq = this.Ext.create("Terrasoft.EntitySchemaQuery", {
						rootSchemaName: "UsrMyEntity"
					});
					esq.addColumn("UsrAccount");
					esq.getEntity(masterRecordId, function(result) {
						var accountId = (result.success && result.entity)
							? result.entity.get("UsrAccount")
							: null;
						callback.call(scope || this, accountId);
					}, this);
				},

				// The link-table contract the mixin needs.
				getMultiSelectLookupConfig: function() {
					return {
						rootEntitySchemaName: "UsrMyEntity",
						rootColumnName: "UsrMyEntity",
						relatedEntitySchemaName: "UsrRelatedEntity",
						relatedColumnName: "UsrRelatedEntity"
					};
				},

				// Narrow what the selection window shows.
				getAdditionalLookupFilters: function() {
					var filterGroup = this.Terrasoft.createFilterGroup();

					var accountId = this.get("UsrParentAccountId");
					if (accountId) {
						filterGroup.add("ByHoldingFilter",
							this.Terrasoft.createColumnFilterWithParameter(
								this.Terrasoft.ComparisonType.EQUAL, "UsrParentAccount", accountId));
					}
					filterGroup.add("ExcludeCancelledFilter",
						this.Terrasoft.createColumnFilterWithParameter(
							this.Terrasoft.ComparisonType.NOT_EQUAL, "UsrStatus",
							"7352911c-9cff-460c-a202-ed8b10fb8ee8"));

					return filterGroup;
				},

				// The rows exist now - fill the columns the mixin did not set.
				onGridDataLoaded: function(response) {
					this.callParent(arguments);
					if (this.get("UsrNeedParentFix")) {
						this.set("UsrNeedParentFix", false);
						this.fillHoldingForNewRecords();
					}
				},

				fillHoldingForNewRecords: function() {
					var masterRecordId = this.getMasterRecordId();
					var accountId = this.get("UsrParentAccountId");
					if (!masterRecordId || !accountId) {
						return;
					}
					var update = this.Ext.create("Terrasoft.UpdateQuery", {
						rootSchemaName: "UsrRelatedInMyEntity"
					});
					update.filters.addItem(
						this.Terrasoft.createColumnFilterWithParameter(
							this.Terrasoft.ComparisonType.EQUAL, "UsrMyEntity", masterRecordId));
					// Only the rows that have no value yet.
					update.filters.addItem(
						this.Terrasoft.createColumnIsNullFilter("UsrParentAccount"));

					update.setParameterValue("UsrParentAccount", accountId,
						this.Terrasoft.DataValueType.GUID);

					update.execute(function(response) {
						if (response.success) {
							this.loadGridData();
						} else {
							console.error("Failed to fill UsrParentAccount", response.errorInfo);
						}
					}, this);
				}
			}
		};
	});
