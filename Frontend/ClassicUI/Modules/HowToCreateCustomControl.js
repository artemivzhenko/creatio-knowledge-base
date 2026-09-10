// --- How to create a custom Classic UI control -------------------------------
// SOURCE: _SalesUp_DT_ITSM/Schemas/SuCaseExtendableLookupEdit - a lookup-style
// edit built on the stock text edit.
//
// A control is a schema of type "Module" whose body defines an Ext class in the
// Terrasoft.controls namespace. Nothing is returned to the page: registering the
// class is the side effect, and pages reach it through
// controlConfig.className.
//
//   define("MyControl", ["ext-base", "terrasoft"], function(Ext) {
//       Ext.define("Terrasoft.controls.MyControl", {
//           extend: "Terrasoft.TextEdit",
//           alternateClassName: "Terrasoft.MyControl",
//           ...
//       });
//   });
//
// Dependencies "ext-base" and "terrasoft" give you Ext and the Terrasoft
// namespace. `alternateClassName` is what you write in controlConfig.
//
// USEFUL BASE CLASSES: Terrasoft.TextEdit, Terrasoft.BaseEdit,
// Terrasoft.LookupEdit, Terrasoft.Button, Terrasoft.Container.
//
// USEFUL MIXINS:
//   Terrasoft.ExpandableList  drop-down list behaviour (expandList/collapseList,
//                             listView, onListElementSelected)
//   Terrasoft.LeftIcon        left icon rendering
//
// THE THREE HOOKS THAT MAKE BINDING WORK. A control that is bound in diff must
// forward its mixin binding contributions, or bindTo silently does nothing:
//   getBindConfig()        merge the mixin bind config into the base one
//   initBinding()          merge the mixin binding into the base binding
//   subscribeForEvents()   let the mixin subscribe to model events
//
// EVENTS. Declare them with addEvents in init and raise them with fireEvent;
// the page binds to them through controlConfig.
//
// LIFECYCLE. Attach DOM handlers in initDomEvents, and release everything in
// onDestroy - a control outlives the page otherwise, because Ext keeps the
// class-level document listeners alive.
//
// Consider this a last resort: a custom control is unsupported surface that
// breaks on upgrades. Try controlConfig on a stock control first.

define("SuCaseExtendableLookupEdit", ["ext-base", "terrasoft"], function(Ext) {

	Ext.define("Terrasoft.controls.SuCaseExtendableLookupEdit", {
		extend: "Terrasoft.TextEdit",
		// The name pages use in controlConfig.className.
		alternateClassName: "Terrasoft.SuCaseExtendableLookupEdit",

		mixins: {
			expandableList: "Terrasoft.ExpandableList",
			leftIcon: "Terrasoft.LeftIcon"
		},

		// Control options, overridable per instance from controlConfig.
		disableInputDrop: true,
		enableLeftIcon: false,
		fireChangeEventsOnPick: true,
		value: "",
		objectValue: "",
		minSearchCharsCount: 3,
		searchDelay: 500,
		maxItemsInView: 0,
		enableLocalFilter: false,

		// --- lifecycle ------------------------------------------------------
		init: function() {
			this.callParent(arguments);

			// Events the page can bind to through controlConfig.
			this.addEvents(
				"loadVocabulary",     // the user asked for the selection window
				"paste",
				"keyPressed",
				"setAdditionalProps"  // a list element was picked
			);

			// Respect the global lookup setting when it is present.
			if (Terrasoft.ControlsSettings &&
				Terrasoft.ControlsSettings.lookupMinSearchCharsCount >= 0) {
				this.minSearchCharsCount = Terrasoft.ControlsSettings.lookupMinSearchCharsCount;
			}
			this.mixins.expandableList.init.call(this);
		},

		initDomEvents: function() {
			this.callParent(arguments);

			this.on("rightIconMouseOver", this.onRightIconMouseOver, this);
			this.on("rightIconMouseOut", this.onRightIconMouseOut, this);

			this.getEl().on("paste", this.onPaste, this);
			// Collapse the list when the user clicks anywhere else.
			Ext.getDoc().on("mousedown", this.onMouseDownCollapse, this);
		},

		onDestroy: function() {
			this.mixins.expandableList.destroy.call(this);
			this.callParent(arguments);
		},

		// --- binding: forward the mixin contributions -----------------------
		getBindConfig: function() {
			var bindConfig = this.callParent(arguments);
			Ext.apply(bindConfig, this.mixins.expandableList.getBindConfig());
			Ext.apply(bindConfig, this.mixins.leftIcon.getBindConfig());
			return bindConfig;
		},

		initBinding: function(configItem, bindingRule, bindConfig) {
			var binding = this.callParent(arguments);
			var lookupBinding = this.mixins.expandableList.initBinding.call(
				this, configItem, bindingRule, bindConfig);
			return Ext.apply(binding, lookupBinding);
		},

		subscribeForEvents: function(binding, property, model) {
			this.callParent(arguments);
			this.mixins.expandableList.subscribeForEvents.call(this, binding, property, model);
		},

		getModelMethod: function(binding, model) {
			return this.mixins.expandableList.getModelMethod.call(this, binding, model);
		},

		// --- value handling -------------------------------------------------
		// changeValue decides whether anything actually changed and raises
		// "change"; setValue additionally updates the DOM.
		changeValue: function(item) {
			var value = this.value;
			var isChanged = (value && item)
				? value !== (item.displayValue || item)
				: value !== item;

			if (isChanged) {
				this.value = (item && item.displayValue) || item || "";
				this.objectValue = Terrasoft.deepClone(item);
				if (this.fireChangeEventsOnPick || !item || !Ext.isObject(item)) {
					this.fireEvent("change", this.objectValue, this);
				}
				this.setClearIconVisibility();
			}
			return isChanged;
		},

		setValue: function(value) {
			var isChanged = this.changeValue(value);
			if (!isChanged || !this.rendered) {
				return;
			}
			this.setDomValue((value && value.displayValue) || value || "");

			if (this.objectValue && Ext.isObject(this.objectValue)) {
				this.fireEvent("setAdditionalProps", this.objectValue, this);
			}
		},

		// Always encode what you push into the DOM.
		getInitValue: function() {
			var value = this.value;
			var displayValue = value
				? Terrasoft.getTypedStringValue(value, Terrasoft.DataValueType.TEXT)
				: "";
			return displayValue ? Terrasoft.encodeHtml(displayValue) : "";
		},

		// --- keyboard -------------------------------------------------------
		onKeyDown: function(e) {
			if (!this.enabled) {
				return;
			}
			this.mixins.expandableList.onKeyDown.call(this, e, true);

			switch (e.getKey()) {
				case e.DOWN:
					if (!this.listView || !this.listView.visible) {
						this.expandList(this.typedValue);
					}
					break;
				case e.ENTER:
					if (e.ctrlKey || e.altKey || e.shiftKey) {
						break;
					}
					if (this.listView && this.listView.visible && this.listView.selectedItem) {
						this.listView.fireEvent("listPressEnter");
					} else {
						this.collapseList();
						// Ask the page to open the selection window.
						this.fireEvent("loadVocabulary", { searchValue: this.typedValue });
					}
					break;
			}
		},

		// Debounced search: only filter after searchDelay and enough characters.
		onKeyUp: function(e) {
			if (!this.enabled) {
				return;
			}
			this.clearTimer("timerId");

			var typedValue = this.getTypedValue();
			if (!e.isNavKeyPress() && e.getKey() !== e.ENTER && typedValue !== this.typedValue) {
				this.typedValue = typedValue;
				if (this.list) {
					this.list.clear();
				}
				this.changeValue(null);
			}
			if (!e.isNavKeyPress() && typedValue) {
				if (typedValue.length > this.minSearchCharsCount) {
					this.timerId = Ext.defer(function() {
						this.expandList(typedValue);
					}, this.searchDelay, this);
				} else {
					this.collapseList();
				}
			}
		},

		onPaste: function(e) {
			this.onKeyUp(e);
		},

		onFocus: function() {
			this.callParent(arguments);
			this.mixins.expandableList.onFocus.call(this);
		},

		onBlur: function() {
			this.mixins.expandableList.onBlur.call(this);
			this.collapseList();
		},

		onMouseDownCollapse: function(e) {
			var isInWrap = e.within(this.getWrapEl());
			var isInList = Ext.isEmpty(this.listView) || e.within(this.listView.getWrapEl());
			if (!isInWrap && !isInList) {
				this.collapseList();
			}
		},

		onRightIconMouseOver: function() {
			if (this.rendered) {
				this.rightIconEl.addCls("lookup-edit-right-icon-hover");
			}
		},

		onRightIconMouseOut: function() {
			if (this.rendered) {
				this.rightIconEl.removeCls("lookup-edit-right-icon-hover");
			}
		},

		setEnabled: function() {
			this.callParent(arguments);
			this.setClearIconVisibility();
		}
	});
});

// --- Using it on a page ------------------------------------------------------
// define("SuChangeLogCaseSettingPageV2", ["SuCaseExtendableLookupEdit"], function() {
//     return {
//         entitySchemaName: "SuChangeLogCaseSetting",
//         diff: [{
//             "operation": "insert",
//             "name": "SuBpmColumnCaption",
//             "values": {
//                 "bindTo": "SuBpmColumnCaption",
//                 "hasClearIcon": true,
//                 "layout": { "colSpan": 12, "rowSpan": 1, "column": 0, "row": 0,
//                             "layoutName": "Header" },
//                 "controlConfig": {
//                     "className": "Terrasoft.SuCaseExtendableLookupEdit",
//                     "rightIconClasses": ["custom-right-item", "lookup-edit-right-icon"],
//                     "rightIconClick": { "bindTo": "openRequestLookup" },
//                     "cleariconclick": { "bindTo": "clearField" }
//                 }
//             },
//             "parentName": "Header",
//             "propertyName": "items",
//             "index": 0
//         }]
//     };
// });
