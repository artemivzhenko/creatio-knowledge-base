using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;
using Terrasoft.Core.Entities.Events;

/// <summary>
/// Demonstrates how to detect column changes and read old values inside an EntityEventListener.
/// GetOldTypedColumnValue&lt;T&gt;() returns the value that was in the database before the current update.
/// GetChangedColumnValues() returns all columns whose value changed in this save operation.
/// Both methods are meaningful only in OnUpdating and OnUpdated — on insert there is no "old" value.
/// Use this to implement audit logging, conditional side effects, or workflow triggers
/// that should only fire when a specific field actually changes.
/// </summary>
namespace Terrasoft.Configuration {

    [EntityEventListener(SchemaName = "Contact")]
    public class ContactColumnChangeEventListener : BaseEntityEventListener {

        public override void OnUpdating(object sender, EntityBeforeEventArgs e) {
            base.OnUpdating(sender, e);
            var entity = (Entity)sender;
            var userConnection = entity.UserConnection;

            // --- Check one specific column ---
            var newStatusId = entity.GetTypedColumnValue<Guid>("StatusId");
            var oldStatusId = entity.GetOldTypedColumnValue<Guid>("StatusId");

            if (newStatusId != oldStatusId) {
                // Status changed — react before the record is written to DB
                // e.g. validate, enrich other fields, trigger a side effect
            }

            // --- Check a text column ---
            var newName = entity.GetTypedColumnValue<string>("Name");
            var oldName = entity.GetOldTypedColumnValue<string>("Name");

            if (newName != oldName) {
                // Name changed
            }

            // --- Iterate all changed columns ---
            // GetChangedColumnValues() returns only the columns that have a new value in this save
            foreach (var changedValue in entity.GetChangedColumnValues()) {
                var columnName = changedValue.Column.Name;
                var newValue   = changedValue.Value;
                // custom logic per changed column
            }
        }
    }
}
