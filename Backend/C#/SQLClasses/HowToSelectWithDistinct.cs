using System;
using System.Collections.Generic;
using System.Data;
using Terrasoft.Common;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to use .Distinct() in the Select query builder to eliminate duplicate rows.
/// Call .Distinct() immediately after new Select() — before adding columns — to emit SELECT DISTINCT.
/// Useful when a join or detail table produces duplicate parent-column values and you only need
/// the unique set (e.g. all unique AccountIds linked to active contacts).
/// </summary>
class HowToSelectWithDistinct {

    // 1. Get unique AccountIds from contacts that match a filter
    public List<Guid> GetUniqueAccountIds(UserConnection userConnection) {
        var select = new Select(userConnection)
                .Distinct()
                .Column("AccountId")
            .From("Contact")
            .Where("IsActive").IsEqual(Column.Parameter(true)) as Select;

        var result = new List<Guid>();

        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            using (IDataReader reader = select.ExecuteReader(dbExecutor)) {
                while (reader.Read()) {
                    result.Add(reader.GetColumnValue<Guid>("AccountId"));
                }
            }
        }

        return result;
    }

    // 2. Distinct on multiple columns — returns unique (AccountId, TypeId) pairs
    public List<(Guid AccountId, Guid TypeId)> GetUniqueAccountTypePairs(UserConnection userConnection) {
        var select = new Select(userConnection)
                .Distinct()
                .Column("AccountId")
                .Column("TypeId")
            .From("Contact")
            .Where("AccountId").Not().IsNull() as Select;

        var result = new List<(Guid, Guid)>();

        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            using (IDataReader reader = select.ExecuteReader(dbExecutor)) {
                while (reader.Read()) {
                    result.Add((
                        reader.GetColumnValue<Guid>("AccountId"),
                        reader.GetColumnValue<Guid>("TypeId")
                    ));
                }
            }
        }

        return result;
    }
}
