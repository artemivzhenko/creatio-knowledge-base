using Terrasoft.Core;

/// <summary>
/// Demonstrates how to retrieve a localizable string defined in a schema's LocalizableStrings section.
/// Use this when you need culture-aware text in backend logic: log messages, exception messages,
/// notification bodies, or any UI-facing text managed through the Creatio translation mechanism.
/// The method automatically returns the value for the current user's UI culture.
/// If the schema or string name is not found, the method returns an empty string.
/// </summary>
class HowToGetLocalizableStringFromSchema {

    public void UseLocalizableString(UserConnection userConnection) {
        // GetLocalizableString(schemaName, stringName) resolves the value for the current user's culture
        // schemaName — the internal name of the schema that owns the LocalizableString resource
        // stringName — the code name of the string as defined in the schema's LocalizableStrings
        string localizedText = userConnection.GetLocalizableString("MySchemaName", "MyStringName");

        if (string.IsNullOrEmpty(localizedText)) {
            // String not found — use a hardcoded fallback or throw
            localizedText = "Fallback text";
        }

        // custom logic: log, send, assign to parameter, etc.
    }
}
