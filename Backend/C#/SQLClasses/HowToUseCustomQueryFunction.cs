using System;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Demonstrates how to call a database function from Select with Func.CustomFunction (CustomQueryFunction).
/// Two traps, both silent until the code runs or compiles:
/// 1. Pass the BARE function name. Func.CustomFunction prepends the default schema itself, so
///    "public.usr_normalize_phone" is sent as public.public.usr_normalize_phone and the database
///    answers "function does not exist" (a 400/500 from the service, not a compile error).
/// 2. A CustomQueryFunction is NOT a QueryColumnExpression. Assigning it to a QueryColumnExpression
///    variable or passing it where only that type is accepted fails to compile (CS1503 / CS0029).
///    Column(), Where(), IsEqual() and the other condition methods have IQueryColumnExpressionConvertible
///    overloads - pass the function straight in; GetQueryColumnExpression() converts it where an API
///    insists on QueryColumnExpression.
/// The arguments are column expressions too: Column.SourceColumn for a column, Column.Parameter for a value.
/// Check the overloads of the installed version with tools/env/api.py (Func CustomFunction, Select Column).
/// The function itself ships as a SQL script of the package (tools/sqlscripts), installed before the code that calls it.
/// </summary>
class HowToUseCustomQueryFunction {

    // The function as the SQL script created it, without its schema.
    private const string NormalizePhoneFunction = "usr_normalize_phone";

    // 1. A function result as a selected column.
    public Select SelectNormalizedPhones(UserConnection userConnection) {
        var normalized = Func.CustomFunction(NormalizePhoneFunction, Column.SourceColumn("c", "Phone"));
        return new Select(userConnection)
            .Column("c", "Id")
            .Column(normalized).As("NormalizedPhone")   // the IQueryColumnExpressionConvertible overload
            .From("Contact").As("c");
    }

    // 2. A function in a condition: records whose normalized phone equals a value.
    public Select SelectByNormalizedPhone(UserConnection userConnection, string phone) {
        return new Select(userConnection)
            .Column("c", "Id")
            .From("Contact").As("c")
            .Where(Func.CustomFunction(NormalizePhoneFunction, Column.SourceColumn("c", "Phone")))
            .IsEqual(Func.CustomFunction(NormalizePhoneFunction, Column.Parameter(phone))) as Select;
    }

    // 3. Where an API takes only QueryColumnExpression: convert explicitly.
    public QueryColumnExpression AsColumnExpression() {
        CustomQueryFunction function = Func.CustomFunction(NormalizePhoneFunction, Column.Parameter("+1 555 0100"));
        // QueryColumnExpression wrong = function;     // does not compile: CustomQueryFunction is not a QueryColumnExpression
        return function.GetQueryColumnExpression();
    }

    // 4. Wrong: the schema is added twice.
    public Select Wrong(UserConnection userConnection) {
        return new Select(userConnection)
            .Column(Func.CustomFunction("public." + NormalizePhoneFunction, Column.SourceColumn("c", "Phone"))).As("X")
            .From("Contact").As("c");
    }
}
