using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to execute a stored procedure and raw SQL using StoredProcedure and CustomQuery.
/// Use StoredProcedure when you need to call a procedure defined in the database.
/// Use CustomQuery when you need to execute an arbitrary SQL string with full control over the query.
/// Both bypass entity event handlers and permissions — use only when ESQ or the query builder
/// cannot express what you need, or when raw performance is critical.
/// </summary>
class HowToExecuteStoredProcedureAndCustomQuery {

    // 1. Execute a stored procedure with parameters
    public void ExecuteStoredProcedure(UserConnection userConnection, string param1, int param2) {
        var sp = new StoredProcedure(userConnection, "procedure_name");

        // Pass parameters by name — names must match the procedure's parameter names
        sp.WithParameter("param1", param1);
        sp.WithParameter("param2", param2);

        sp.Execute();
    }

    // 2. Execute a raw SQL string using CustomQuery
    public void ExecuteCustomSql(UserConnection userConnection, string sqlText) {
        var query = new CustomQuery(userConnection, sqlText);

        // EnsureDBConnection() provides a safe, pooled DBExecutor for the current user context
        using (DBExecutor dbExecutor = userConnection.EnsureDBConnection()) {
            query.Execute(dbExecutor);
        }
    }
}
