using System;
using Terrasoft.Core;
using Terrasoft.Core.Configuration;

/// <summary>
/// Demonstrates how to read and write Creatio system settings (SysSettings) from C# code.
/// System settings store configurable values: email addresses, feature flags, IDs, URLs, timeouts, etc.
/// Always read settings through Terrasoft.Core.Configuration.SysSettings — never via raw ESQ/Select
/// against the SysSettings tables.
/// GetValue&lt;T&gt; takes three arguments: the user connection, the setting's Code (as configured in
/// the SysSettings section), and a default value returned when the setting is missing or fails to
/// read — always pass the default explicitly instead of relying on default(T).
/// Use SetValue to update a setting under the current user's context and permissions.
/// Call ClearCache after writing to make the new value visible immediately in the current app context.
/// </summary>
class HowToReadAndWriteSysSettings {

    public void ReadAndWriteSettings(UserConnection userConnection) {
        // --- Reading ---

        // GetValue<T>(userConnection, code, defaultValue) returns the setting value as the specified
        // type (string, int, bool, Guid, DateTime, etc.), falling back to defaultValue when the
        // setting is not configured or cannot be read
        string defaultFromEmail = SysSettings.GetValue(userConnection, "DefaultEmailFromAddress", "no-reply@mycompany.com");

        bool featureEnabled = SysSettings.GetValue(userConnection, "MyFeatureEnabled", false);

        Guid defaultAccountId = SysSettings.GetValue(userConnection, "DefaultAccountId", Guid.Empty);

        // --- Writing ---

        // SetValue updates the setting in the database under the current user context
        SysSettings.SetValue(userConnection, "DefaultEmailFromAddress", "no-reply@mycompany.com");

        SysSettings.SetValue(userConnection, "MyFeatureEnabled", true);

        // --- Cache ---

        // SysSettings are cached per application context — clear after writing so the new value
        // is used immediately without waiting for an application restart
        SysSettings.ClearCache(userConnection);
    }
}
