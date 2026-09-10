// --- Base detail methods (BaseDetailV2 / BaseGridDetailV2) -------------------
// Source: Creatio Academy "BaseDetailV2 schema" and "BaseGridDetailV2 schema"
// references, cross-checked against the detail schemas in this repository.
//
// INHERITANCE. BaseDetailV2 is the generic detail; BaseGridDetailV2 adds the
// list (grid) behaviour and REPLACES several BaseDetailV2 methods - init,
// initData and updateDetail among them. A grid detail therefore has both sets.
//
// ============================ BaseDetailV2 ===================================
//
// init(callback, scope)              initialises the detail
// initProfile()                      initialises the schema profile
//                                    (Terrasoft.emptyFn by default)
// initDefaultCaption()               sets the default detail title
// initDetailOptions()                initialises the list view data collection
// initData(callback, scope)          initialises the data collection
// subscribeSandboxEvents()           subscribes to the messages the detail needs
// getUpdateDetailSandboxTags()       builds the tag array for UpdateDetail
// updateDetail(config)               updates the detail from the passed config
// getEditPageName()                  returns the record page name for the
//                                    selected record type - override to route
//                                    different types to different pages
// onDetailCollapsedChanged(isCollapsed)  expand / collapse handler
// getToolsVisible()                  returns the collapse state; commonly reused
//                                    as the condition for custom buttons
// getDetailInfo()                    publishes the message that fetches detail data
//
// ========================== BaseGridDetailV2 =================================
//
// init(callback, scope)              registers messages, initialises filters
// initData(callback, scope)          initialises the list view model collection
// loadGridData()                     loads the list data
// initGridData()                     initialises list management defaults
// getGridData()                      returns the list collection
// getFilters()                       returns the detail filter collection
// getActiveRow()                     id of the selected row
// addRecord(editPageUId)             adds a record; saves the record page first
//                                    when needed - the usual override point
// copyRecord(editPageUId)            copies the record and opens its page
// editRecord(record)                 opens the page of the selected record
// openCard(operation, typeColumnValue, recordId)   opens a record page
// onCardSaved()                      handles the save event of the record page
//                                    the detail opened; also fires when the
//                                    MASTER page finishes saving, which is what
//                                    makes the "save master, then continue"
//                                    pattern work
// addToolsButtonMenuItems(toolsButtonMenu)  adds items to the tools drop-down
// initDetailFilterCollection()       initialises the detail filter
// setFilter(key, value)              sets a detail filter value
// loadQuickFilter(config)            loads the quick filter
// subscribeSandboxEvents()           message subscriptions
// destroy()                          clears data and unloads the detail
//
// OBSERVED IN THIS REPO but not on the reference page:
// getAddRecordButtonVisible()        visibility of the add button; often
//                                    implemented as `return this.getToolsVisible();`
// onGridDataLoaded(response)         fires after the rows are loaded - the place
//                                    for post-load fixes
// getMasterRecordId()                id of the master record
// onActiveRowAction(tag, recordId)   row button dispatcher of an editable grid
//                                    (see Details/HowToMakeDetailEditableInline.js)
//
// ============================== ATTRIBUTES ===================================
//
// BaseDetailV2:
//   CanAdd, CanEdit, CanDelete   (BOOLEAN)  permission flags
//   Collection    (COLLECTION)   the detail data
//   Filter        (CUSTOM_OBJECT) the detail filter
//   DetailColumnName (STRING)    column used to filter the data
//   MasterRecordId (GUID)        THE PARENT RECORD KEY - read it with
//                                this.get("MasterRecordId")
//   IsDetailCollapsed (BOOLEAN)
//   DefaultValues (CUSTOM_OBJECT) default column values for new records
//   Caption       (STRING)       detail title
//
// BaseGridDetailV2:
//   ActiveRow     (GUID)         active row id
//   IsGridEmpty   (BOOLEAN)
//   MultiSelect   (BOOLEAN)      multi-selection on/off
//   SelectedRows  (COLLECTION)   selected records
//   RowCount      (INTEGER)
//   IsPageable    (BOOLEAN)      paging on/off - remember that getGridData()
//                                then returns only the loaded page
//   SortColumnIndex (INTEGER)
//   CardState     (TEXT)         record page opening mode
//   EditPageUId   (GUID)
//   DetailFilters (COLLECTION)
//   IsDetailWizardAvailable (BOOLEAN)

define("QSMyDetail", [], function() {
	return {
		entitySchemaName: "QSServicesInOrder",
		methods: {

			init: function() {
				this.callParent(arguments);
			},

			// Reuse the collapse state as the button condition.
			getAddRecordButtonVisible: function() {
				return this.getToolsVisible();
			},

			// Gate the add action and explain the refusal.
			addRecord: function() {
				if (!this.get("CanAdd")) {
					this.showInformationDialog(this.get("Resources.Strings.CannotAddRecordMessage"));
					return;
				}
				this.callParent(arguments);
			},

			// Route record types to different edit pages.
			getEditPageName: function() {
				var type = this.get("ActiveRowType");
				return type === "special" ? "QSSpecialServicePage" : this.callParent(arguments);
			},

			// Post-load fix-up.
			onGridDataLoaded: function(response) {
				this.callParent(arguments);
				if (this.get("NeedsPostLoadFix")) {
					this.set("NeedsPostLoadFix", false);
					this.applyPostLoadFix();
				}
			},

			// Reading the master record id.
			getMasterId: function() {
				return this.get("MasterRecordId");
			},

			applyPostLoadFix: function(){},

			destroy: function() {
				this.callParent(arguments);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
