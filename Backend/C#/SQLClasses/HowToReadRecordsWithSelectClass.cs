using System;
using System.Collections.Generic;
using System.Data;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to read records using the Select query builder (raw SQL layer).
/// Use this approach instead of ESQ when you need:
///   - maximum read performance with no rights-checking overhead;
///   - joins or aggregations that ESQ does not support natively;
///   - a single scalar value without materialising a full entity.
/// WARNING: Select bypasses row- and column-level permissions — use ESQ when security matters.
/// </summary>
class HowToReadRecordsWithSelectClass {

    // 1. Read a collection of records into a typed DTO list
    public List<MyEntityDto> GetRecentRecords(UserConnection userConnection, int daysBack) {
        var select = new Select(userConnection)
                .Column("Id")
                .Column("MyField1")
                .Column("MyField2")
            .From("MyEntity")
            .Where("CreatedOn").IsGreater(Column.Parameter(DateTime.UtcNow.AddDays(-daysBack)))
            .OrderByDesc("CreatedOn") as Select;

        var result = new List<MyEntityDto>();

        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            using (IDataReader dataReader = select.ExecuteReader(dbExecutor)) {
                while (dataReader.Read()) {
                    var id       = dataReader.GetColumnValue<Guid>("Id");
                    var myField1 = dataReader.GetColumnValue<string>("MyField1");
                    var myField2 = dataReader.GetColumnValue<DateTime>("MyField2");

                    result.Add(new MyEntityDto {
                        Id       = id,
                        MyField1 = myField1,
                        MyField2 = myField2
                    });
                }
            }
        }

        return result;
    }

    // 2. Read a single scalar value using ExecuteScalar — no DataReader needed
    public string GetRecordName(UserConnection userConnection, Guid recordId) {
        var select = new Select(userConnection)
                .Column("Name")
            .From("MyEntity")
            .Where("Id").IsEqual(Column.Parameter(recordId)) as Select;

        // ExecuteScalar reads the first column of the first row
        // Returns default(T) if the query returns no rows
        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            return select.ExecuteScalar<string>(dbExecutor);
        }
    }
}

// DTO for mapping raw DataReader rows — keep it close to the query that fills it
class MyEntityDto {
    public Guid     Id       { get; set; }
    public string   MyField1 { get; set; }
    public DateTime MyField2 { get; set; }
}
