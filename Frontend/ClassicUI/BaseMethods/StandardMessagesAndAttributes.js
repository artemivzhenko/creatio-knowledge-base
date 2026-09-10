// --- Standard sandbox messages and base attributes ---------------------------
// Source: Creatio Academy BasePageV2 / BaseDetailV2 / BaseGridDetailV2 message
// tables, cross-checked against the schemas in this repository.
//
// These messages already exist in the base schemas. To USE one you still declare
// it in your own `messages` section with the direction YOU need - subscribing to
// a message the base publishes, or publishing one the base subscribes to.
//
// ===================== PUBLISHED BY A DETAIL, HANDLED BY THE PAGE ============
//
//   GetCardState        PTP        ask the page for its card state. Returns an
//                                  object whose `state` is a
//                                  ConfigurationEnums.CardStateV2 value - this
//                                  is how a detail learns the master record is
//                                  still unsaved (ADD / COPY).
//   SaveRecord          PTP        ask the page to save. Args:
//                                  { isSilent: true, messageTags: [sandbox.id] }
//                                  When the save finishes the page fires
//                                  onCardSaved on the detail.
//   IsCardChanged       PTP        does the page have unsaved changes?
//   DetailChanged       PTP        tell the page the detail data changed
//   OpenCard            PTP        ask the page to open a record page
//   GetColumnsValues    PTP        ask the page for column values; the page's
//                                  handler RETURNS them (see
//                                  Messaging/HowToCommunicateDetailWithPage.js)
//   UpdateCardProperty  PTP        change a value in the page view model
//   GetEntityInfo       PTP        request the master record data
//   ValidateCard        PTP        ask the page to validate itself
//
// ===================== SUBSCRIBED BY A DETAIL ================================
//
//   UpdateDetail        PTP        the page asks the detail to refresh
//   CardSaved           broadcast  a record page was saved
//   getCardInfo         PTP        returns record page data
//   UpdateFilter        broadcast  update the detail filters
//   InitFilterFromStorage / LoadedFiltersFromStorage
//                                  stored filter lifecycle
//   GetExtendedFilterConfig / GetModuleSchema
//                                  custom filter configuration
//
// ===================== PAGE-LEVEL MESSAGES (BasePageV2) ======================
//
//   CloseCard, OpenCard, OpenCardInChain, GetCardState, IsCardChanged,
//   ValidateCard, UpdateCardProperty, UpdateCardHeader,
//   UpdatePageHeaderCaption, GridRowChanged, ReloadSectionRow,
//   GetActiveViewName, GetColumnInfo, GetEntityColumnChanges,
//   GetMiniPageMasterEntityInfo, GetPageTips, CanChangeHistoryState,
//   IsEntityChanged, IsDcmFilterColumnChanged, UpdateParentLookupDisplayValue,
//   ReInitializeActionsDashboard, ReloadDashboardItems, ReloadDashboardItemsPTP
//
// ===================== BASE ATTRIBUTES WORTH KNOWING =========================
//
// On a page (BasePageV2):
//   Id                       primary key; empty until the first save
//   CardState                ADD / EDIT / COPY (ConfigurationEnums.CardStateV2)
//   IsChanged                marks the record dirty
//   ActiveTabName            the selected tab
//   IsCardOpenedAttribute    used by generated business rules
//   IsPageHeaderVisible, IsLeftModulesContainerVisible,
//   IsActionDashboardContainerVisible, HasActiveDcm,
//   ActionsDashboardAttributes, PageHeaderColumnNames, GridDataViewName,
//   AnalyticsDataViewName, IsNotAvailable, CanCustomize, Operation,
//   EntityReloadScheduled
//
// On a detail: see BaseMethods/DetailBaseMethods.js (MasterRecordId, ActiveRow,
// MultiSelect, SelectedRows, CanAdd/CanEdit/CanDelete, ...).
//
// A note on `this.values`: joined ESQ columns land in the raw values map under
// their DOTTED key, so a column added as "QSWorkplaceTab.QSTabTitle" is read as
// this.values["QSWorkplaceTab.QSTabTitle"], not with this.get("QSTabTitle").

// ====================== WORKED EXAMPLE: save master, then act ================
// A detail that must not add rows until the master record exists.

define("QSMyDetail", ["ConfigurationEnums"], function(configurationEnums) {
	return {
		entitySchemaName: "QSOrdersInComplexAgr",

		messages: {
			"GetCardState": {
				mode: Terrasoft.MessageMode.PTP,
				direction: Terrasoft.MessageDirectionType.PUBLISH
			},
			"SaveRecord": {
				mode: Terrasoft.MessageMode.PTP,
				direction: Terrasoft.MessageDirectionType.PUBLISH
			}
		},

		attributes: {
			"QSPendingAddRecord": {
				dataValueType: Terrasoft.DataValueType.BOOLEAN,
				value: false
			}
		},

		methods: {

			addRecord: function() {
				// Ask the page what state it is in.
				var masterCardState = this.sandbox.publish("GetCardState", null, [this.sandbox.id]);
				var isNewRecord = masterCardState && (
					masterCardState.state === configurationEnums.CardStateV2.ADD ||
					masterCardState.state === configurationEnums.CardStateV2.COPY);

				if (isNewRecord) {
					// Remember the intent, ask the page to save, and continue in
					// onCardSaved once the save completes.
					this.set("QSPendingAddRecord", true);
					this.sandbox.publish("SaveRecord",
						{ isSilent: true, messageTags: [this.sandbox.id] },
						[this.sandbox.id]);
					return;
				}
				this.proceed();
			},

			// Fires when the master page finishes saving - manual Save and the
			// programmatic SaveRecord above both land here.
			onCardSaved: function() {
				if (this.get("QSPendingAddRecord")) {
					this.set("QSPendingAddRecord", false);
					this.proceed();
				}
			},

			proceed: function() {}
		}
	};
});
