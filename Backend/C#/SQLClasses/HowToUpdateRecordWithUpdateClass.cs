using System;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to update a record using the Update query builder (raw SQL layer).
/// Use this approach instead of the Entity model when:
///   - you need maximum performance (no entity event handlers are triggered);
///   - you are doing a mass update and don't need business logic to run;
///   - you must update specific columns without loading the full entity first.
/// WARNING: Update bypasses all entity event handlers (Saving, Saved, etc.).
/// </summary>
class HowToUpdateRecordWithUpdateClass {

    public void UpdateRecord(UserConnection userConnection, Guid recordId, string newValue) {
        var update = new Update(userConnection, "MyEntity")
            // --- Fields to change ---
            .Set("MyField1",     Column.Parameter(newValue))
            .Set("MyField2",     Column.Parameter(DateTime.UtcNow))

            // --- Mandatory system columns ---
            .Set("ModifiedOn",   Column.Parameter(DateTime.UtcNow))
            .Set("ModifiedById", Column.Parameter(userConnection.CurrentUser.Id))

            .Where("Id").IsEqual(Column.Parameter(recordId)) as Update;

        // Execute returns the number of affected rows
        int affectedRows = update.Execute();

        if (affectedRows != 1) {
            // Handle failure: log, throw, or return false to the caller
            throw new InvalidOperationException(
                $"Expected to update 1 row in MyEntity, but {affectedRows} rows were affected.");
        }
    }
}
