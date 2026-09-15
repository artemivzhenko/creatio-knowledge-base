using System;
using System.Globalization;
using Terrasoft.Common;
using Terrasoft.Core.Process;

/// <summary>
/// Demonstrates how to read and write business process parameters of all supported types
/// inside a Script Task element.
/// Get&lt;T&gt;("ParameterName") reads the current value; Set&lt;T&gt;("ParameterName", value) writes it back.
/// Both methods are process instance methods — available only inside a Script Task.
/// The parameter must be declared in the process designer with a matching type.
/// Supported types: int, decimal, DateTime, Guid, bool, string, LocalizableString, CompositeObjectList.
/// </summary>
class HowToWorkWithScriptTaskParameters {

    // Paste this method body into the Script Task element in the process designer
    public bool Execute(ProcessExecutingContext context) {

        // --- Integer ---
        int intValue = Get<int>("IntegerParameter");
        Set("IntegerParameter", intValue + 5);

        // --- String (Text) ---
        string textValue = Get<string>("TextParameter");
        Set("TextParameter", textValue + " updated");

        // --- Guid (Lookup) ---
        Guid lookupValue = Get<Guid>("LookupParameter");
        if (lookupValue == Guid.Empty) {
            // Read a system value — CurrentUserContact is a built-in system value
            lookupValue = (Guid)UserConnection.SystemValueManager
                .GetValue(UserConnection, "CurrentUserContact");
            Set("LookupParameter", lookupValue);
        }

        // --- DateTime ---
        DateTime dateTime = Get<DateTime>("DateTimeParameter");
        Set("DateTimeParameter", dateTime.AddDays(1));

        // --- Decimal (also used for Currency parameters) ---
        decimal decValue = Get<decimal>("DecimalParameter");
        Set("DecimalParameter", decValue + 5.5m);

        // --- Boolean ---
        bool boolValue = Get<bool>("BooleanParameter");
        Set("BooleanParameter", !boolValue);

        // --- LocalizableString ---
        LocalizableString locValue = Get<LocalizableString>("LocalizableStringParameter");
        locValue.SetCultureValue(CultureInfo.GetCultureInfo("en-US"), "Hello");
        locValue.SetCultureValue(CultureInfo.GetCultureInfo("fr-FR"), "Bonjour");
        Set("LocalizableStringParameter", locValue);

        // --- CompositeObjectList (collection or record list parameter) ---
        var list = new CompositeObjectList<CompositeObject>();
        var item = new CompositeObject();
        item["Field1"] = "Value1";
        item["Field2"] = 42;
        list.Add(item);
        Set("CollectionParameter", list);

        // Return true to allow the process flow to continue to the next element
        return true;
    }
}
