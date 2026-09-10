// --- Base validation methods (per-column validators) -------------------------
// Source: Creatio Academy - "Implement the validation of a String type field on
// a record page" and "Implement the validation of a Date/Time type field".
//
// Creatio has THREE validation layers. Pick the narrowest one that fits.
//
//   1. Business rules            declarative required / visible / enabled
//                                (see BusinessRules/)
//   2. Column validators         per-field checks, run as the user types and
//                                again on save; the message appears UNDER the
//                                field. This file.
//   3. validate / asyncValidate  page-wide checks on save; the message appears
//                                in a dialog (see BaseMethods/PageLifecycleMethods.js
//                                and Lifecycle/HowToInterceptSaveAndValidate.js)
//
// THE CONTRACT
//   setValidationConfig()   overridden base method that binds validators to
//                           columns. Call this.callParent(arguments) FIRST,
//                           otherwise the base page loses its own validators.
//   addColumnValidator(columnName, validatorFn)
//                           binds one validator to one column.
//   validatorFn()           runs with the view model as `this`. Return an
//                           object:
//                             { invalidMessage: "..." }  -> invalid, the string
//                                                           is shown under the
//                                                           field and in the
//                                                           save error box
//                             { invalidMessage: "" }     -> valid
//
// Always return the object - returning undefined is treated as invalid by some
// controls and produces an empty error bubble.
//
// A validator is synchronous. If the check needs a server round trip, do it in
// asyncValidate instead; a validator cannot wait for an ESQ.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			// Bind the validators. Parent first.
			setValidationConfig: function() {
				this.callParent(arguments);
				this.addColumnValidator("QSPhone", this.phoneValidator);
				this.addColumnValidator("QSDueDate", this.dueDateValidator);
				this.addColumnValidator("QSCreatedOn", this.dueDateValidator);
			},

			// String validator: a message means invalid, an empty string means OK.
			phoneValidator: function() {
				var invalidMessage = "";
				var value = this.get("QSPhone");

				if (value && !/^\+?[0-9\s\-()]{7,20}$/.test(value)) {
					invalidMessage = this.get("Resources.Strings.WrongPhoneFormatMessage");
				}
				return { invalidMessage: invalidMessage };
			},

			// Cross-field validator: the same function is bound to BOTH columns
			// so editing either one re-runs the check.
			dueDateValidator: function() {
				var invalidMessage = "";
				var dueDate = this.get("QSDueDate");
				var createdOn = this.get("QSCreatedOn");

				if (dueDate && createdOn && dueDate < createdOn) {
					invalidMessage = this.get("Resources.Strings.DueDateBeforeCreatedOnMessage");
				}
				return { invalidMessage: invalidMessage };
			},

			// A required-style check is better expressed as a business rule or a
			// bound `required` property; use a validator only when the condition
			// is more than "not empty".
			amountValidator: function() {
				var invalidMessage = "";
				var amount = this.get("QSAmount");
				var hasDiscount = this.get("QSHasDiscount");

				if (hasDiscount && (amount == null || amount <= 0)) {
					invalidMessage = this.get("Resources.Strings.AmountRequiredWithDiscountMessage");
				}
				return { invalidMessage: invalidMessage };
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});
