using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to paginate ESQ results using RowCount and SkipRowCount.
/// RowCount sets the page size — number of records returned per query.
/// SkipRowCount offsets the result set for page-by-page navigation.
/// UseOffsetFetchPaging must be true — without it SkipRowCount is silently ignored
/// and the query returns from the first row every time.
/// Always sort on a stable column when paginating to guarantee consistent ordering across pages.
/// </summary>
class HowToPaginateWithESQ {

    // Return one page of contacts sorted by Name
    // pageNumber is zero-based: 0 = first page, 1 = second page, etc.
    public EntityCollection GetPage(UserConnection userConnection, int pageNumber, int pageSize) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Contact");

        // Sort is mandatory for stable pagination — result order is undefined without it
        var nameCol = esq.AddColumn("Name");
        nameCol.OrderByAsc(0);

        esq.AddColumn("Email");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        // Number of records to return (page size)
        esq.RowCount = pageSize;

        // Number of records to skip (page offset)
        esq.SkipRowCount = pageNumber * pageSize;

        // Required to activate OFFSET/FETCH paging — SkipRowCount has no effect without this
        esq.UseOffsetFetchPaging = true;

        return esq.GetEntityCollection(userConnection);
    }

    // Convenience overload: get total record count to calculate total pages on the caller side
    public int GetTotalCount(UserConnection userConnection) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Contact");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;
        return esq.GetEntityCollection(userConnection).Count;
    }
}
