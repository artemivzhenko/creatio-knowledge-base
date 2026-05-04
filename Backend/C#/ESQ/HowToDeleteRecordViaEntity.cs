using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to delete a record using the Entity model.
/// Use this approach when entity event handlers (Deleting, Deleted) must fire —
/// they will not trigger if you use the Delete query builder from SQLClasses.
/// FetchFromDB is required before Delete() to load the record into the entity instance.
/// Returns true on success, false if the record was not found or the delete operation failed.
/// </summary>
class HowToDeleteRecordViaEntity {

    // 1. Delete a single record by Id
    public bool DeleteById(UserConnection userConnection, Guid recordId) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("MyEntity")
            .CreateEntity(userConnection);

        if (!entity.FetchFromDB(recordId)) {
            // Record not found — nothing to delete
            return false;
        }

        // Delete() fires Deleting → executes DB DELETE → fires Deleted event handlers
        return entity.Delete();
    }

    // 2. Delete a record located by a non-primary column value
    public bool DeleteByColumn(UserConnection userConnection, string code) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("MyEntity")
            .CreateEntity(userConnection);

        if (!entity.FetchFromDB("Code", code)) {
            return false;
        }

        return entity.Delete();
    }
}
