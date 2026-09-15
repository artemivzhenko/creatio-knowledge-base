using System;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to wrap multiple database operations in an explicit transaction.
/// Use an explicit transaction when two or more write operations must succeed or fail together —
/// if any operation fails the entire set is rolled back, leaving the database consistent.
/// Pass the same DBExecutor to every query inside the transaction so they share one connection.
/// Always call RollbackTransaction() in the catch block — uncommitted transactions
/// that are abandoned will be rolled back by the DB server, but calling it explicitly
/// makes the intent clear and releases the connection faster.
/// </summary>
class HowToUseExplicitTransaction {

    public void InsertTwoRecordsAtomically(UserConnection userConnection, string nameA, string nameB) {
        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            dbExecutor.StartTransaction();
            try {
                // Both inserts run on the same connection inside the same transaction
                new Insert(userConnection)
                    .Into("MyEntity")
                    .Set("Id",   Column.Parameter(Guid.NewGuid()))
                    .Set("Name", Column.Parameter(nameA))
                    .Execute(dbExecutor);

                new Insert(userConnection)
                    .Into("MyEntity")
                    .Set("Id",   Column.Parameter(Guid.NewGuid()))
                    .Set("Name", Column.Parameter(nameB))
                    .Execute(dbExecutor);

                // Both operations succeeded — commit
                dbExecutor.CommitTransaction();
            }
            catch {
                // Any failure rolls back both inserts
                dbExecutor.RollbackTransaction();
                throw;
            }
        }
    }

    // Mixing Insert and Update inside one transaction
    public void CreateAndUpdateAtomically(UserConnection userConnection, Guid parentId, string childName) {
        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            dbExecutor.StartTransaction();
            try {
                new Insert(userConnection)
                    .Into("ChildEntity")
                    .Set("Id",          Column.Parameter(Guid.NewGuid()))
                    .Set("Name",        Column.Parameter(childName))
                    .Set("ParentId",    Column.Parameter(parentId))
                    .Execute(dbExecutor);

                new Update(userConnection, "ParentEntity")
                    .Set("ModifiedOn",   Column.Parameter(DateTime.UtcNow))
                    .Set("ModifiedById", Column.Parameter(userConnection.CurrentUser.Id))
                    .Where("Id").IsEqual(Column.Parameter(parentId))
                    .Execute(dbExecutor);

                dbExecutor.CommitTransaction();
            }
            catch {
                dbExecutor.RollbackTransaction();
                throw;
            }
        }
    }
}
