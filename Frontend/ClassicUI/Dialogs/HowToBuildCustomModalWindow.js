// --- How to build a custom modal window ---------------------------------------
// Classic UI has no declarative modal for arbitrary content. When the standard
// dialogs are not enough (a table to fill in, a multi-step form), pages build
// the modal as raw DOM and append it to document.body.
//
// This is a heavy technique. Prefer, in order:
//   1. showConfirmationDialog / showInformationDialog for a question or a notice.
//   2. A separate edit page opened from the record.
//   3. A business process with a pre-configured page.
//   4. Only then a hand-built modal.
//
// THE PATTERN
//   - build the markup, append one root node to document.body
//   - inject a <style> element once, guarded by its id, so repeated opens do not
//     stack stylesheets
//   - keep a `self` reference to the view model; DOM handlers do not get it
//   - remove the node AND every global you created when closing
//
// THE TRAP: inline onclick="window.someFn()" needs a global function, so pages
// assign closures to `window`. Those globals outlive the page and keep the whole
// view model alive. If you use this style, delete the globals on close, as
// closeModal below does. addEventListener is the cleaner alternative.
//
// Block the underlying page while the modal is open by covering it with the
// overlay element, not with MaskHelper - the mask would grey out your modal too.

define("QSMyDetail", [], function() {
	return {
		entitySchemaName: "QSAdditionalServices",
		methods: {

			openCalculationsModal: function(config) {
				var self = this;

				this.addModalStyles();

				var modalHtml =
					'<div id="qs-calculations-modal" class="qs-modal-overlay">' +
						'<div class="qs-modal-content">' +
							'<div class="qs-modal-header">' +
								'<h3 class="qs-modal-title">Preliminary calculations</h3>' +
								'<div class="qs-modal-buttons">' +
									'<button type="button" class="qs-modal-cancel">Cancel</button>' +
									'<button type="button" class="qs-modal-create">Create</button>' +
								'</div>' +
							'</div>' +
							'<div class="qs-modal-body"><div id="qs-calculations-table"></div></div>' +
						'</div>' +
					'</div>';

				var wrapper = document.createElement("div");
				wrapper.innerHTML = modalHtml;
				var modal = wrapper.firstElementChild;
				document.body.appendChild(modal);

				this.renderCalculationsTable(config);

				// Prefer listeners over inline onclick + window globals.
				modal.querySelector(".qs-modal-cancel").addEventListener("click", function() {
					self.closeCalculationsModal();
				});
				modal.querySelector(".qs-modal-create").addEventListener("click", function() {
					self.createCalculations(config);
				});

				// Clicking the backdrop must not silently discard user input.
				modal.addEventListener("click", function(e) {
					if (e.target === modal) {
						Terrasoft.showInformation("Use Cancel to close the window");
					}
				});
			},

			closeCalculationsModal: function() {
				var modal = document.getElementById("qs-calculations-modal");
				if (modal) {
					modal.remove();
				}
				// If you assigned closures to window, delete them here.
				delete window.qsCreateCalculations;
				delete window.qsCloseCalculationsModal;
			},

			// Inject the stylesheet once per session.
			addModalStyles: function() {
				if (document.getElementById("qs-modal-styles")) {
					return;
				}
				var style = document.createElement("style");
				style.id = "qs-modal-styles";
				style.textContent =
					".qs-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.4);" +
					"display:flex;align-items:center;justify-content:center;z-index:10000;}" +
					".qs-modal-content{background:#fff;border-radius:4px;min-width:720px;" +
					"max-height:80vh;overflow:auto;}" +
					".qs-modal-header{display:flex;justify-content:space-between;" +
					"align-items:center;padding:12px 16px;border-bottom:1px solid #e0e0e0;}";
				document.head.appendChild(style);
			},

			renderCalculationsTable: function(config) {},

			createCalculations: function(config) {
				// Read the values out of the DOM, write them with an InsertQuery
				// or a BatchQuery, then close and refresh.
				this.closeCalculationsModal();
				this.reloadGridData();
			},

			// A modal outlives nothing: tear it down with the page.
			destroy: function() {
				this.closeCalculationsModal();
				this.callParent(arguments);
			}
		}
	};
});
