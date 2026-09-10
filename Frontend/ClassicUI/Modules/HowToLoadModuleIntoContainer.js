// --- How to load a Classic UI module into a container ------------------------
// SOURCE: _SalesUp_Base/Schemas/SuFreedomFilterEditModule and
// SuBaseFreedomTimerModule - both host a stock Classic UI (7.x) module.
//
// The sandbox can mount any module into a DOM container:
//
//   var moduleId = this.sandbox.loadModule("<ModuleName>", {
//       renderTo: <container element or id>,
//       id:       <unique instance id>
//   });
//   ...
//   this.sandbox.unloadModule(moduleId, <the same renderTo>);
//
// Always pass your own `id`. Two instances of the same module with the same id
// collide, and without an id you cannot address the instance with tagged
// messages. The convention is `this.sandbox.id + "_<ModuleName>"`, which is
// unique per hosting module instance.
//
// Always unload. A module left mounted keeps its subscriptions and its DOM, and
// the next mount renders on top of the old one.
//
// TALKING TO THE LOADED MODULE: subscribe BEFORE loading it, using the instance
// id as the tag, so the module finds a listener the moment it starts asking for
// its configuration. A PTP message returns a value, which is how the hosted
// module pulls its config:
//
//   this.sandbox.subscribe("GetFilterModuleConfig",
//       () => this._getFilterModuleConfig(), null, [this._moduleId]);
//
// Stock modules worth knowing: "FilterEditModule" (the filter builder),
// "StructureExploreModuleV2" (column picker, normally opened through
// StructureExplorerUtilities - see Fields/HowToOpenStructureExplorer.js).
//
// FREEDOM UI HOST. The example below is the bridge form: a web component that
// extends Base7xViewElement, which supplies `sandbox`, `initContext` and
// `getMessages` so a legacy module can live inside a Freedom UI page. In a plain
// Classic UI schema you call the same sandbox methods directly from init and
// destroy, without the web-component wrapper.

define("SuFreedomFilterEditModule",
	["@creatio-devkit/common", "Base7xViewElement", "ckeditor-base"],
	function(sdk, Base7xViewElement) {

		class SuFreedomFilterEditModule extends Base7xViewElement {

			// Inputs the host page binds to.
			set filterData(value) { this._filterData = value; }
			get filterData() { return this._filterData; }

			set displayFilterData(value) { this._displayFilterData = value; }
			get displayFilterData() { return this._displayFilterData; }

			set filterRootSchemaName(value) { this._filterRootSchemaName = value; }
			get filterRootSchemaName() { return this._filterRootSchemaName; }

			set onFilterDataChanged(value) { this._onFilterDataChanged = value; }
			get onFilterDataChanged() { return this._onFilterDataChanged; }

			constructor() {
				super("SuFreedomFilterEditModule");
			}

			connectedCallback() {
				super.connectedCallback();
				this._init();
			}

			_init() {
				this.initContext(() => {
					this._moduleId = this.sandbox.id + "_SuFreedomFilterEditModule";

					// Subscribe BEFORE loading, tagged with the instance id.
					this.sandbox.subscribe("GetFilterModuleConfig",
						() => this._getFilterModuleConfig(), null, [this._moduleId]);
					this.sandbox.subscribe("OnFiltersChanged",
						(args) => this._onFiltersChanged(args), null, [this._moduleId]);

					this._loadFilterEditModule();
				});
			}

			_loadFilterEditModule() {
				this._moduleId = this.sandbox.loadModule("FilterEditModule", {
					renderTo: this._renderTo,
					id: this._moduleId
				});
			}

			// PTP handler: the return value IS the answer the module receives.
			_getFilterModuleConfig() {
				return {
					filters: this._displayFilterData,
					rootSchemaName: this._filterRootSchemaName
				};
			}

			// The filter object serialises in two flavours: without manager info
			// for storage, with it for display.
			_onFiltersChanged(args) {
				const filter = args && args.filter;
				if (!filter) {
					return;
				}
				const filterData = filter.serialize({ serializeFilterManagerInfo: false });
				const displayFilterData = filter.serialize({ serializeFilterManagerInfo: true });
				this._onFilterDataChanged(filterData, displayFilterData);
			}

			// Declare the message contract, merged with the base one.
			getMessages() {
				const messages = super.getMessages();
				return Object.assign(messages, {
					"GetFilterModuleConfig": {
						mode: Terrasoft.MessageMode.PTP,
						direction: Terrasoft.MessageDirectionType.SUBSCRIBE
					},
					"OnFiltersChanged": {
						mode: Terrasoft.MessageMode.BROADCAST,
						direction: Terrasoft.MessageDirectionType.SUBSCRIBE
					}
				});
			}

			// Unmount with the SAME renderTo that was used to load.
			disconnectedCallback() {
				this.sandbox.unloadModule(this._moduleId, this._renderTo);
			}
		}

		customElements.define("su-filteredit", SuFreedomFilterEditModule);

		sdk.registerViewElement({
			type: "su.SuFreedomFilterEditModule",
			selector: "su-filteredit",
			inputs: {
				filterData: {},
				displayFilterData: {},
				filterRootSchemaName: {},
				onFilterDataChanged: {}
			}
		});

		return Terrasoft.SuFreedomFilterEditModule;
	});
