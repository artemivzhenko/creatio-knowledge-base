// --- Base section methods (BaseSectionV2) ------------------------------------
// Source: Creatio Academy "BaseSectionV2 schema" reference and the section
// customization guide, plus the section schemas in this repository.
//
// Every section schema (SchemaType "ModuleViewModelSchema") inherits
// BaseSectionV2, implemented in the NUI package. A section renders in two modes
// - combined (list + preview) and separate (full-screen list) - and much of the
// customisation work is remembering that both modes have their own elements.
//
// ============================== METHODS ======================================
//
// init()                             base schema initialisation; the place for
//                                    per-entity switches in a replacing section
// initFixedFiltersConfig()           builds the fixed-filter block: create a
//                                    config object with a `filters` array and
//                                    assign it to the fixedFiltersConfig
//                                    attribute of the view model
// getEditPageName()                  returns the record page to open for the
//                                    selected row - override to route by type
// onCardSaved()                      handles the save event of the record page
//                                    opened from the section
// getFilters()                       returns the section list filters
// reloadGridData()                   re-reads the list; call it after writing
//                                    records directly with an InsertQuery
// checkCanManageAnalytics()          resolves the CanManageAnalytics permission
//                                    (system operation "Analytics setup")
// onCanManageAnalytics(result)       sets the CanManageAnalytics attribute
//
// ============================== ATTRIBUTES ===================================
//
// Analytics-related, from the reference:
//   ChartEditSchemaName (TEXT), IsEmptyChart (BOOLEAN),
//   AnalyticsChartActiveRow (GUID), AnalyticsGridData (COLLECTION),
//   IsAnalyticsPrintButtonVisible (BOOLEAN), AnalyticsData (COLLECTION),
//   IsAnalyticsActionButtonsContainerVisible (BOOLEAN),
//   AnalyticsDataViewName (TEXT), IsBindDataActionVisible (BOOLEAN)
//
// ============================== MESSAGES =====================================
//
//   RerenderModule        (PTP, publish)      re-render the dashboard module
//   ReloadDataOnRestore   (broadcast, subscribe)  refresh data on next launch
//   SelectedPackageResult (PTP, subscribe)    selected result data
//
// ========================= VIEW ELEMENT NAMES ================================
// Not methods, but the names you target from diff. Both modes must be handled:
//
//   CombinedModeAddRecordButton                the "+" in combined mode
//   CombinedModeActionButtonsCotainer          (stock name, with the typo)
//   SeparateModeAddRecordButton                the "+" in separate mode
//   SeparateModeActionButtonsLeftContainer
//   SeparateModeActionButtonsRightContainer
//   ActionButtonsContainer, DataGrid, SectionFilterContainer
//
// See Sections/HowToCustomiseSectionModesAndButtons.js for the worked example.

define("QSMyEntitySection", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			init: function() {
				this.callParent(arguments);
				// A replacing section serves every inheriting entity - narrow it.
				this.set("SuCustomButtonVisible", this.entitySchemaName === "QSMyEntity");
			},

			// Fixed filters shown above the list.
			initFixedFiltersConfig: function() {
				var fixedFilterConfig = {
					entitySchemaName: "QSMyEntity",
					filters: [
						{
							name: "PeriodFilter",
							caption: this.get("Resources.Strings.PeriodFilterCaption"),
							dataValueType: Terrasoft.DataValueType.DATE,
							startDate: { columnName: "QSStartDate" },
							dueDate: { columnName: "QSDueDate" }
						},
						{
							name: "Owner",
							caption: this.get("Resources.Strings.OwnerFilterCaption"),
							dataValueType: Terrasoft.DataValueType.LOOKUP,
							columnName: "QSOwner",
							defValue: Terrasoft.SysValue.CURRENT_USER_CONTACT
						}
					]
				};
				this.set("FixedFilterConfig", fixedFilterConfig);
			},

			// Route rows to different edit pages by type.
			getEditPageName: function() {
				var type = this.get("ActiveRowTypeColumnValue");
				return type === "special" ? "QSSpecialPage" : this.callParent(arguments);
			},

			onCardSaved: function() {
				this.callParent(arguments);
				this.reloadGridData();
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
