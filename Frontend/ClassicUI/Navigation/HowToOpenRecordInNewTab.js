// --- How to open a record's card in a new browser tab --------------------------
// Three ways, three different results:
//
//   1. NEW BROWSER TAB - window.open with the shell address of the card:
//        Terrasoft.workspaceBaseUrl + "/Nui/ViewModule.aspx#CardModuleV2/<PageSchema>/edit/<recordId>"
//      The new tab loads the whole application again (a second session tab):
//      the current page, its unsaved changes and its sandbox are untouched.
//      <PageSchema> is the edit page's SCHEMA name (UsrMyEntity1Page), not the
//      object name; a wrong one opens an empty shell with no error.
//
//   2. SAME TAB, the card replaces the current view - publish PushHistoryState
//      with the same hash (without "#"); the browser Back button returns here.
//
//   3. SAME TAB, chained to the current card - openCardInChain: the opened
//      card closes back to this one (the way a detail opens its records). Use
//      it for "edit the related record and come back", never for a new tab.
//
// Open the new tab straight from the click handler: a window.open called later
// from an async callback (after an ESQ or a service call) is treated as a
// pop-up and blocked silently by the browser. Read what you need first, or open
// the tab at once and navigate it when the answer comes.
//
// A new record has no Id until it is saved: check isNewMode() first.

define("UsrMyEntity1Page", [], function() {
	return {
		entitySchemaName: "UsrMyEntity",
		methods: {

			// 1. New browser tab with the related record's card.
			onOpenRelatedInNewTabClick: function() {
				var related = this.get("UsrRelatedEntity");
				if (!related) {
					return;
				}
				var url = Terrasoft.workspaceBaseUrl + "/Nui/ViewModule.aspx#CardModuleV2/UsrRelatedEntity1Page/edit/" + related.value;
				window.open(url, "_blank");
			},

			// 2. Same tab, replacing the current view.
			openRelatedHere: function(recordId) {
				this.sandbox.publish("PushHistoryState", {
					hash: "CardModuleV2/UsrRelatedEntity1Page/edit/" + recordId
				});
			},

			// 3. Same tab, chained: closing the opened card comes back here.
			openRelatedInChain: function(recordId) {
				this.openCardInChain({
					schemaName: "UsrRelatedEntity1Page",
					operation: "edit",
					id: recordId,
					moduleId: this.sandbox.id + "_CardModuleV2"
				});
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
