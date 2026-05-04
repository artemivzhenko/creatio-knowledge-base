using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;
using Terrasoft.Core.Entities.Events;

/// <summary>
/// Demonstrates how to block a record from being saved using an EntityEventListener.
/// Use OnInserting, OnUpdating, or OnSaving to validate data server-side before the DB write.
/// Throwing an exception immediately stops the operation — the message is surfaced to the user
/// or returned to the API caller, making it the recommended approach for hard validation errors.
/// This logic cannot be bypassed by client scripts or direct API calls.
/// </summary>
namespace Terrasoft.Configuration {

    [EntityEventListener(SchemaName = "Contact")]
    public class ContactEventListener : BaseEntityEventListener {

        public override void OnInserting(object sender, EntityBeforeEventArgs e) {
            var entity = (Entity)sender;
            var userConnection = entity.UserConnection;

            // Block save if Email is empty — throw stops the insert and shows the message to the user
            string email = entity.GetTypedColumnValue<string>("Email");
            if (string.IsNullOrWhiteSpace(email)) {
                throw new Exception("Email is required for a new contact.");
            }

            // Block save if Name exceeds the allowed length
            string name = entity.GetTypedColumnValue<string>("Name");
            if (name != null && name.Length > 250) {
                throw new Exception("Contact name must not exceed 250 characters.");
            }

            base.OnInserting(sender, e);
        }

        public override void OnUpdating(object sender, EntityBeforeEventArgs e) {
            var entity = (Entity)sender;
            var userConnection = entity.UserConnection;

            // Example: prevent deactivation of contacts that have open activities
            bool isActive = entity.GetTypedColumnValue<bool>("IsActive");
            if (!isActive) {
                // custom check against DB if needed using userConnection
                // throw new Exception("Cannot deactivate a contact with open activities.");
            }

            base.OnUpdating(sender, e);
        }
    }
}
