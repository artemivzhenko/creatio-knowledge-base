using System.Globalization;
using Terrasoft.Common;
using Terrasoft.Core.Process;

/// <summary>
/// Demonstrates how to read and write a LocalizableString process parameter inside a Script Task.
/// Use this when a business process parameter holds culture-specific text (e.g. notification messages,
/// UI labels) and you need to set different values per language from backend code.
/// Get&lt;T&gt;() and Set&lt;T&gt;() are process instance methods — they are available only inside
/// a Script Task element and access parameters defined on the process by their code name.
/// The parameter must be declared in the process as type LocalizableString.
/// </summary>
class HowToSetLocalizableStringInScriptTask {

    // Paste this method body into the Script Task element in the process designer.
    // ProcessExecutingContext is provided automatically by the process engine.
    public bool Execute(ProcessExecutingContext context) {
        // Read the current value of the LocalizableString process parameter by its code name
        LocalizableString localizableStringValue = Get<LocalizableString>("LocalizableStringParameter");

        // Set a translation for each culture you want to support
        localizableStringValue.SetCultureValue(CultureInfo.GetCultureInfo("en-US"), "Hello!");
        localizableStringValue.SetCultureValue(CultureInfo.GetCultureInfo("fr-FR"), "Bonjour!");
        localizableStringValue.SetCultureValue(CultureInfo.GetCultureInfo("de-DE"), "Hallo!");

        // Write the updated LocalizableString back to the process parameter
        Set("LocalizableStringParameter", localizableStringValue);

        // Return true to allow the process flow to continue to the next element
        return true;
    }
}
