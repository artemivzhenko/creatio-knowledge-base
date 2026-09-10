// --- How to reach the rendered DOM from a Classic UI schema ------------------
// USE THIS ONLY AS A LAST RESORT. Anything expressible through diff bindings,
// attributes or business rules must be done there: DOM code breaks on every
// Creatio upgrade, has no test coverage, and leaks listeners across pages.
//
// It is nevertheless a real pattern in large Classic UI pages, for things the
// declarative layer cannot express - overlaying a stock detail button,
// reacting to a group being collapsed, injecting a custom widget into a tab.
//
// ELEMENT IDS follow the schema names, which is what makes this possible:
//   #<SchemaName><ElementName>-wrapperEl          a control wrapper
//   #<SchemaName>AddRecordButtonButton-wrapperEl  a detail add button
//   #<SchemaName>DetailControlGroup               a detail group container
//   #<SchemaName>DetailControlGroup-caption_      its caption element
//
// THE THREE RULES
//   1. The DOM does not exist when init runs, and often not when
//      onEntityInitialized runs either. Poll for the node with a short
//      setTimeout retry, or observe the parent - never assume it is there.
//   2. Mark nodes you have already wired (a data-* attribute) so a re-render
//      does not attach the same handler twice.
//   3. Disconnect every observer, clear every interval, and remove every
//      listener in destroy(). Store them on the view model (an attribute of
//      type CUSTOM_OBJECT, or a plain instance field) so you can find them.
//
// Never write values into the DOM to change data. Write to the view model with
// this.set(...) and let the binding update the control.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",

		attributes: {
			// Somewhere to keep the observer so destroy() can reach it.
			"CurrentObserver": {
				"dataValueType": Terrasoft.DataValueType.CUSTOM_OBJECT,
				"value": null
			}
		},

		methods: {

			onEntityInitialized: function() {
				this.callParent(arguments);
				this.waitForDetailAndAttach();
			},

			// Rule 1: poll until the node appears, then wire it.
			waitForDetailAndAttach: function() {
				var self = this;
				var attempt = function() {
					var node = document.querySelector("#QSMyDetailDetailControlGroup");
					if (!node) {
						setTimeout(attempt, 500);
						return;
					}
					self.attachDetailObserver(node);
					self.attachAddButtonHandler();
				};
				attempt();
			},

			// Observe a container for re-renders and re-apply the customisation.
			attachDetailObserver: function(targetNode) {
				// Replace an earlier observer instead of stacking them.
				var previous = this.get("CurrentObserver");
				if (previous) {
					previous.disconnect();
				}

				var self = this;
				var observer = new MutationObserver(function(mutations) {
					// Debounce: a single expand produces a burst of mutations.
					if (self._domTimeout) {
						clearTimeout(self._domTimeout);
					}
					self._domTimeout = setTimeout(function() {
						self.applyDetailCustomisation();
					}, 100);
				});

				observer.observe(targetNode, {
					attributes: true,
					childList: true,
					subtree: true
				});

				this.set("CurrentObserver", observer);
			},

			// Rule 2: idempotent wiring, marked on the node itself.
			attachAddButtonHandler: function() {
				var button = document.querySelector("#QSMyDetailAddRecordButtonButton-wrapperEl");
				if (!button) {
					setTimeout(this.attachAddButtonHandler.bind(this), 100);
					return;
				}
				if (button.getAttribute("data-qs-handler-setup") === "true") {
					return;
				}
				button.setAttribute("data-qs-handler-setup", "true");

				var self = this;
				button.addEventListener("click", function(e) {
					if (!self.get("IsAddAllowed")) {
						e.stopPropagation();
						self.showInformationDialog(
							self.get("Resources.Strings.CannotAddRecordMessage"));
					}
				}, { capture: true });
			},

			applyDetailCustomisation: function() {},

			// Rule 3: tear everything down.
			destroy: function() {
				var observer = this.get("CurrentObserver");
				if (observer) {
					observer.disconnect();
					this.set("CurrentObserver", null);
				}
				if (this._domTimeout) {
					clearTimeout(this._domTimeout);
					this._domTimeout = null;
				}
				this.callParent(arguments);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
