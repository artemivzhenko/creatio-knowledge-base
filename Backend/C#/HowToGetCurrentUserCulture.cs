using Terrasoft.Core;

/// <summary>
/// Demonstrates how to get the current user's culture (locale) from UserConnection.
/// Use this when you need to apply language-specific logic: formatting dates or numbers,
/// selecting the correct localizable resource, or routing to culture-specific code paths.
/// The culture reflects the UI language the user selected in their Creatio profile settings.
/// Falls back to "en-US" if the culture is not set.
/// </summary>
class HowToGetCurrentUserCulture {

    public string GetUserCultureName(UserConnection userConnection) {
        // Culture.Name returns the IETF language tag, e.g. "en-US", "de-DE", "uk-UA"
        string cultureName = userConnection.CurrentUser.Culture.Name;

        // Always add a fallback — Culture.Name can be empty for system or anonymous users
        return string.IsNullOrEmpty(cultureName) ? "en-US" : cultureName;
    }
}
