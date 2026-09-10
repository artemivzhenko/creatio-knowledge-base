// --- Ext, Terrasoft and lodash helpers available in every schema -------------
// Classic UI ships Ext JS, the Terrasoft namespace and lodash globally. Knowing
// them saves reinventing utilities and keeps schemas idiomatic.
//
// TYPE CHECKS AND FLOW (Ext)
//   Ext.isEmpty(v)        true for null, undefined, "" and []
//   Ext.isObject(v)       plain object check
//   Ext.isFunction(v)     function check
//   Ext.isArray(v)
//   Ext.callback(fn, scope, args)  call an OPTIONAL callback; a no-op when fn is
//                                  undefined - preferred over an if() guard
//   Ext.defer(fn, ms, scope)       deferred call that returns a timer id you can
//                                  cancel; the framework-friendly setTimeout
//   Ext.apply(dest, src)           shallow merge, returns dest
//   Ext.String.format(str, a, b)   "{0} of {1}" style formatting
//
// SERIALISATION (Ext)
//   Ext.decode(jsonString)  parse - used on server message bodies
//   Ext.encode(object)      stringify
//
// OBJECT CREATION (Ext)
//   Ext.create("Terrasoft.EntitySchemaQuery", { ... })
//   Ext.define("Terrasoft.controls.MyControl", { ... })
//   Ext.getDoc(), Ext.get(id)   Ext element wrappers around the DOM
//
// TERRASOFT HELPERS
//   Terrasoft.deepClone(value)          deep copy; use before storing a lookup
//                                       object you did not create
//   Terrasoft.GUID_EMPTY                "00000000-0000-0000-0000-000000000000"
//   Terrasoft.generateGUID()            new guid for a client-side id
//   Terrasoft.encodeHtml(text)          escape before writing into the DOM
//   Terrasoft.getTypedStringValue(v, t) format a value for display by data type
//   Terrasoft.each(collection, fn)      iterate a Terrasoft.Collection
//   Terrasoft.filter(array, fn, scope)  filter helper
//   Terrasoft.chain(fn1, fn2, ..., scope)  sequential async steps
//                                          (Lifecycle/HowToChainAsyncOperations)
//   Terrasoft.createFilterGroup()
//   Terrasoft.createColumnFilterWithParameter(comparison, path, value)
//   Terrasoft.MaskHelper.ShowBodyMask() / HideBodyMask()
//   Terrasoft.SysValue.CURRENT_USER / CURRENT_USER_CONTACT
//   Terrasoft.DataValueType, Terrasoft.ComparisonType,
//   Terrasoft.LogicalOperatorType, Terrasoft.ViewItemType,
//   Terrasoft.ContentType, Terrasoft.MessageMode,
//   Terrasoft.MessageDirectionType, Terrasoft.MessageBoxButtons,
//   Terrasoft.ViewModelColumnType, Terrasoft.controls.ButtonEnums.style
//
// LODASH is exposed as `_`, so _.findKey, _.groupBy, _.uniqBy and friends are
// available without a dependency.
//
// this.Terrasoft / this.Ext also work inside a view model and are equivalent to
// the globals; the prefixed form is the safer habit in code that may run in an
// isolated context.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Optional callback without an if().
			loadData: function(callback, scope) {
				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "QSServicesInOrder"
				});
				esq.addColumn("Id");
				esq.getEntityCollection(function(result) {
					Ext.callback(callback, scope || this, [result]);
				}, this);
			},

			// Deferred call you can cancel.
			scheduleRefresh: function() {
				this.clearScheduledRefresh();
				this._refreshTimerId = Ext.defer(function() {
					this.reloadEntity();
				}, 500, this);
			},

			clearScheduledRefresh: function() {
				if (this._refreshTimerId) {
					clearTimeout(this._refreshTimerId);
					this._refreshTimerId = null;
				}
			},

			// Cloning a lookup before storing it, so a later mutation of the
			// source cannot reach your copy.
			cacheStatus: function() {
				this._cachedStatus = Terrasoft.deepClone(this.get("QSStatus"));
			},

			// Guarding against the empty guid, which is not the same as null.
			hasRealValue: function(columnName) {
				var value = this.get(columnName);
				return !Ext.isEmpty(value) && value.value !== Terrasoft.GUID_EMPTY;
			},

			// Formatting a localizable string with placeholders.
			buildMessage: function(caption) {
				return Ext.String.format(
					this.get("Resources.Strings.ConfirmDeleteMessage"), caption);
			},

			// Numeric data type -> its name, via lodash.
			getTypeNameByNumber: function(number) {
				var key = _.findKey(Terrasoft.DataValueType, function(value) {
					return value === number;
				});
				return key ? key : "";
			},

			destroy: function() {
				this.clearScheduledRefresh();
				this.callParent(arguments);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
