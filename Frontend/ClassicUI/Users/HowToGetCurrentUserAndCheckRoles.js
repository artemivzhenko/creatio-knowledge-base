// --- How to read the current user and check their roles ----------------------
// Terrasoft.SysValue holds the well-known system values available on the client
// without a request. The two you need most:
//
//   Terrasoft.SysValue.CURRENT_USER          - the SysAdminUnit (login) record
//   Terrasoft.SysValue.CURRENT_USER_CONTACT  - the Contact of the current user
//
// Both are lookup-shaped: { value: "<guid>", displayValue: "<name>" }. Use
// .value when writing into a GUID column or comparing ids.
//
// ROLES are not on the client. To find out whether the user belongs to a role
// you query SysUserInRole with an ESQ:
//
//   SysUser  = Terrasoft.SysValue.CURRENT_USER.value
//   SysRole  = the role id (SysAdminUnit id of the role)
//
// The query is asynchronous, so store the answer in a virtual boolean attribute
// and bind the UI to that attribute rather than trying to return a value.
// Call it from onEntityInitialized.
//
// Note that SysUserInRole holds DIRECT membership. Roles inherited through an
// organisational hierarchy are resolved server-side; if you need the effective
// set, do the check in a business process or a service instead.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",

		attributes: {
			"IsUserInSpecificRoles": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN,
				"value": false
			}
		},

		methods: {

			onEntityInitialized: function() {
				this.callParent(arguments);
				this.checkUserRoles();
			},

			readCurrentUser: function() {
				var userId    = Terrasoft.SysValue.CURRENT_USER.value;
				var contactId = Terrasoft.SysValue.CURRENT_USER_CONTACT.value;
				var contactName = Terrasoft.SysValue.CURRENT_USER_CONTACT.displayValue;

				// Writing the current contact into a lookup column.
				this.set("QSResponsible", {
					value: contactId,
					displayValue: contactName
				});

				return { userId: userId, contactId: contactId };
			},

			// Is the current user in any of the listed roles?
			checkUserRoles: function() {
				var specificRoles = [
					"2f8e9ddf-5bd4-498c-8b1d-fb983bb5c715", // SSK SD
					"2cb75460-8c3a-4e8f-a40f-154f099229d5", // Sales managers
					"0ac24ff0-a308-48c7-9500-c63434846a9e"  // DE.unit
				];

				var esq = Ext.create("Terrasoft.EntitySchemaQuery", {
					rootSchemaName: "SysUserInRole"
				});
				esq.addColumn("SysRole");

				// Restrict to the current user.
				esq.filters.add("UserFilter", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "SysUser",
					Terrasoft.SysValue.CURRENT_USER.value));

				// Any of the roles - an OR group with unique keys.
				var roleFilter = Terrasoft.createFilterGroup();
				roleFilter.logicalOperation = Terrasoft.LogicalOperatorType.OR;
				specificRoles.forEach(function(roleId, index) {
					roleFilter.add("RoleFilter" + index,
						Terrasoft.createColumnFilterWithParameter(
							Terrasoft.ComparisonType.EQUAL, "SysRole", roleId));
				});
				esq.filters.add("RoleGroup", roleFilter);

				esq.getEntityCollection(function(result) {
					var isInRole = result.success && result.collection.getItems().length > 0;
					this.set("IsUserInSpecificRoles", isInRole);
				}, this);
			}
		},

		diff: /**SCHEMA_DIFF*/[
			{
				// The UI reacts to the attribute, not to the query.
				"operation": "merge",
				"name": "QSInternalCommentBlock",
				"values": {
					"visible": { "bindTo": "IsUserInSpecificRoles" }
				}
			}
		]/**SCHEMA_DIFF*/
	};
});
