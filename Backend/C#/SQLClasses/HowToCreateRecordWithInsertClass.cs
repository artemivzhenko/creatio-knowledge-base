using System;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to insert a record directly using the Insert query builder (raw SQL layer).
/// Use this approach instead of the Entity model when:
///   - you need maximum performance (no entity event handlers are triggered);
///   - you are doing a bulk insert and don't need business logic to run;
///   - you must explicitly control system columns (CreatedOn, CreatedById, etc.).
/// WARNING: Insert bypasses all entity event handlers (Saving, Saved, etc.).
/// </summary>
class HowToCreateRecordWithInsertClass {

    public void CreateRecord(UserConnection userConnection) {
        // System columns must be set manually — there is no SetDefColumnValues() here
        var now = DateTime.UtcNow;
        var currentUserId = userConnection.CurrentUser.Id;

        Insert insert = new Insert(userConnection)
            .Into("MyEntity")                                          // DB table name (usually matches schema name)
            .Set("Id",           Column.Parameter(Guid.NewGuid()))     // primary key

            // --- String field ---
            .Set("Name",         Column.Parameter("Some text value"))

            // --- DateTime field ---
            .Set("StartDate",    Column.Parameter(now))

            // --- Integer field ---
            .Set("SortOrder",    Column.Parameter(10))

            // --- Decimal field ---
            .Set("Amount",       Column.Parameter(99.99m))

            // --- Boolean field ---
            .Set("IsActive",     Column.Parameter(true))

            // --- Lookup field (Guid of the related record) ---
            .Set("ContactId",    Column.Parameter(Guid.Parse("00000000-0000-0000-0000-000000000000")))

            // --- Mandatory system columns ---
            .Set("CreatedOn",    Column.Parameter(now))
            .Set("CreatedById",  Column.Parameter(currentUserId))
            .Set("ModifiedOn",   Column.Parameter(now))
            .Set("ModifiedById", Column.Parameter(currentUserId));

        // Execute returns the number of affected rows
        int affectedRows = insert.Execute();
        if (affectedRows != 1) {
            // Handle failure: log, throw, or return false to the caller
            throw new InvalidOperationException("Failed to insert record into MyEntity.");
        }
    }
}
