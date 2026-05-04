using System;
using Terrasoft.Core;
using Terrasoft.Core.Configuration;

/// <summary>
/// Demonstrates how to read and write Creatio system settings (SysSettings) from C# code.
/// System settings store configurable values: email addresses, feature flags, IDs, URLs, timeouts, etc.
/// Use GetValue&lt;T&gt; for strong-typed reads without manual conversion.
/// Use SetValue to update a setting under the current user's context and permissions.
/// Call ClearCache after writing to make the new value visible immediately in the current app context.
/// </summary>
class HowToReadAndWriteSysSettings {

    public void ReadAndWriteSettings(UserConnection userConnection) {
        // --- Reading ---

        // GetValue<T> returns the setting value as the specified type (string, int, bool, Guid, DateTime, etc.)
        // The second argument is the setting's Code as configured in the SysSettings section
        string defaultFromEmail = SysSettings.GetValue<string>(userConnection, "DefaultEmailFromAddress");

        bool featureEnabled = SysSettings.GetValue<bool>(userConnection, "MyFeatureEnabled");

        Guid defaultAccountId = SysSettings.GetValue<Guid>(userConnection, "DefaultAccountId");

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
