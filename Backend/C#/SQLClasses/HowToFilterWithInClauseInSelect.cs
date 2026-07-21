using System;
using System.Collections.Generic;
using System.Data;
using Terrasoft.Common;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to filter records by a collection of values using Column.Parameters() and .In().
/// Use this when you need SQL "WHERE col IN (a, b, c, ...)" with a dynamic list.
/// Column.Parameters() converts any IEnumerable&lt;T&gt; to an array of typed query parameters,
/// protecting against SQL injection and handling empty/single-element lists correctly.
/// Works with Select, Update, and Delete query builders.
/// </summary>
class HowToFilterWithInClauseInSelect {

    // 1. Select records whose Id is in a given list
    public List<string> GetNamesByIds(UserConnection userConnection, List<Guid> ids) {
        var select = new Select(userConnection)
                .Column("Id")
                .Column("Name")
            .From("MyEntity")
            .Where("Id").In(Column.Parameters(ids)) as Select;

        var result = new List<string>();

        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            using (IDataReader reader = select.ExecuteReader(dbExecutor)) {
                while (reader.Read()) {
                    result.Add(reader.GetColumnValue<string>("Name"));
                }
            }
        }

        return result;
    }

    // 2. Select with additional AND conditions alongside the IN clause
    public List<Guid> GetActiveRecordsByIds(UserConnection userConnection, List<Guid> ids) {
        var select = new Select(userConnection)
                .Column("Id")
            .From("MyEntity")
            .Where("Id").In(Column.Parameters(ids))
            .And("IsActive").IsEqual(Column.Parameter(true)) as Select;

        var result = new List<Guid>();

        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            using (IDataReader reader = select.ExecuteReader(dbExecutor)) {
                while (reader.Read()) {
                    result.Add(reader.GetColumnValue<Guid>("Id"));
                }
            }
        }

        return result;
    }

    // 3. Bulk update: set a field for all records in the list
    public void BulkUpdateByIds(UserConnection userConnection, List<Guid> ids, string newValue) {
        new Update(userConnection, "MyEntity")
            .Set("MyField",      Column.Parameter(newValue))
            .Set("ModifiedOn",   Column.Parameter(DateTime.UtcNow))
            .Set("ModifiedById", Column.Parameter(userConnection.CurrentUser.Id))
            .Where("Id").In(Column.Parameters(ids))
            .Execute();
    }

    // 4. Bulk delete: remove all records whose Id is in the list
    public void BulkDeleteByIds(UserConnection userConnection, List<Guid> ids) {
        new Delete(userConnection)
            .From("MyEntity")
            .Where("Id").In(Column.Parameters(ids))
            .Execute();
    }
}
