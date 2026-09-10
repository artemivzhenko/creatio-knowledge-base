// --- Base page methods you can override (BasePageV2 / BaseEntityPage) --------
// A Classic UI record page inherits BasePageV2, which itself builds on
// BaseEntityPage. Overriding one of the methods below is the supported way to
// hook into the page; almost every override must call this.callParent(arguments).
//
// Sources: Creatio Academy "BasePageV2 schema" reference, plus the overrides
// observed across the packages in this repository. Methods marked [ACADEMY] are
// in the official reference; [OBSERVED] ones are used in production schemas here
// but are not in that particular reference page.
//
// ============================ LIFECYCLE, IN ORDER ============================
//
// init(callback, scope)                                            [OBSERVED]
//     The view model exists. THE ENTITY IS NOT LOADED: this.get("Id") and every
//     entity column are undefined. Use for wiring only - sandbox subscriptions,
//     Terrasoft.ServerChannel listeners, module-level state, DOM observers.
//     Always this.callParent(arguments) FIRST.
//
// onRender()                                                       [OBSERVED]
//     Comes from the Ext JS Component layer, fired around the render pass. It
//     does NOT guarantee the page is fully rendered and it can fire more than
//     once, so it is a poor place for DOM work; poll for the node instead
//     (see Dom/HowToReachTheDomFromASchema.js). Observed use in this repo is
//     forcing a fresh read: onRender -> this.reloadEntity().
//
// onEntityInitialized()                                            [OBSERVED]
//     The record is loaded and every column is readable. THIS is where page
//     logic belongs: computing flags, defaulting values on a new record,
//     selecting the active tab, starting ESQ lookups.
//     Runs AGAIN after reloadEntity(), so make it idempotent.
//
// ============================== SAVE PIPELINE ================================
//
// save(config)                                                     [OBSERVED]
//     Entry point, also fired by the Save button. Override for side effects
//     (publish a message, notify a detail), not for validation.
//
// validate()                                                       [OBSERVED]
//     Synchronous validation. Return false to stop the save.
//
// asyncValidate(callback, scope)                                   [OBSERVED]
//     Asynchronous validation - the hook for checks that need a server round
//     trip. Contract: this.callParent([wrapper, scope]); inside the wrapper
//     check this.validateResponse(response), run your own checks, then call
//     callback.call(scope, response). Reject by calling back with
//     { success: false, message: "..." }.
//
// setValidationConfig()                                            [ACADEMY]
//     Binds per-column validators. Call this.callParent(arguments) FIRST so the
//     base validators survive, then this.addColumnValidator("Column", this.myValidator).
//     See PageValidationMethods.js.
//
// saveEntity(callback, scope)                                      [OBSERVED]
//     Issues the save request. Override to log or wrap the request.
//
// getSaveQuery()                                                   [OBSERVED]
//     Returns the query object that saveEntity executes - useful for logging
//     what is about to be written.
//
// validateSaveEntityResponse(response, callback, scope)            [OBSERVED]
//     Inspects the server answer. response.success / response.errorInfo.
//
// onSaved(response, config)                                        [ACADEMY]
//     Runs after a successful save. The place for post-save side effects.
//
// onDiscardChangesClick(callback, scope)                           [ACADEMY]
//     Handles the Discard button.
//
// onCanBeDestroyed(cacheKey)                                       [ACADEMY]
//     Checks for unsaved data before the page closes. Edit the cached
//     config.result to allow or block closing.
//
// onValidateCard()                                                 [ACADEMY]
//     Shows the error message when the page is invalid.
//
// ============================== MODE AND DATA ================================
//
// isAddMode() / isCopyMode() / isEditMode()                        [OBSERVED]
//     Current card state. Equivalent explicit form:
//     this.get("CardState") === ConfigurationEnums.CardStateV2.ADD
//
// reloadEntity()                                                   [OBSERVED]
//     Re-reads the record; triggers onEntityInitialized again.
//
// onReloadCard(defaultValues)                                      [ACADEMY]
//     Reloads the data of the add page entity.
//
// updateDetail(config)                                             [OBSERVED]
//     Refreshes one detail: this.updateDetail({ detail: "<detailsKey>" }).
//
// getIncrementCode(callback)                                       [OBSERVED]
//     Terrasoft.BasePageV2.getIncrementCode - generates the next number from
//     the numbering mask configured for the entity. See
//     Data/HowToGenerateIncrementCode.js.
//
// setActiveTab(tabName)                                            [OBSERVED]
//     Switches the active tab. Call from onEntityInitialized.
//
// onGetColumnInfo(columnName)                                      [ACADEMY]
//     Returns column information.
//
// getParameters(parameters) / setParameters(parameters)            [ACADEMY]
//     Bulk read / write of view model parameters.
//
// ============================= HEADER AND VIEWS ==============================
//
// initPageHeaderColumnNames()                                      [ACADEMY]
// getTabsContainerVisible()                                        [ACADEMY]
// getDataViews()                                                   [ACADEMY]
// addChangeDataViewOptions(viewOptions)                            [ACADEMY]
// addSectionDesignerViewOptions(viewOptions)                       [ACADEMY]
// getPrintMenuItemVisible(reportId)                                [ACADEMY]
// getReportFilters()                                               [ACADEMY]
// getLookupModuleId()                                              [ACADEMY]
//
// ============================== PROCESSES ====================================
//
// runProcess(tag)                                                  [ACADEMY]
// runProcessWithParameters(config)                                 [ACADEMY]
//     Start a business process from the page. For the common case prefer
//     ProcessModuleUtilities.executeProcess - see Processes/.
//
// ============================== TEARDOWN =====================================
//
// destroy()                                                        [OBSERVED]
//     Detach everything init attached: server-channel listeners, observers,
//     timers, DOM handlers. Call this.callParent(arguments) LAST.

define("QSMyEntity1Page", ["ConfigurationEnums"], function(enums) {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			init: function() {
				this.callParent(arguments);
				// wiring only - no entity data yet
			},

			// Observed pattern: force a fresh read of the record on render.
			onRender: function() {
				this.callParent(arguments);
				this.reloadEntity();
			},

			onEntityInitialized: function() {
				this.callParent(arguments);

				if (this.isAddMode() || this.isCopyMode()) {
					this.getIncrementCode(function(response) {
						this.set("QSNumber", response);
					});
				}
				this.setActiveTab("NotesAndFilesTab");
			},

			save: function() {
				this.callParent(arguments);
				this.sandbox.publish("OrderFilesSaveChange", null, ["order-file"]);
			},

			validate: function() {
				if (this.get("QSAmount") < 0) {
					this.showInformationDialog(this.get("Resources.Strings.AmountMustBePositive"));
					return false;
				}
				return this.callParent(arguments);
			},

			onSaved: function(response, config) {
				this.callParent(arguments);
				this.updateDetail({ detail: "QSSchema2d707869Detailacdf157e" });
			},

			// Explicit card-state check, equivalent to isAddMode().
			isNewRecord: function() {
				return this.get("CardState") === enums.CardStateV2.ADD;
			},

			destroy: function() {
				// release listeners / timers here
				this.callParent(arguments);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
