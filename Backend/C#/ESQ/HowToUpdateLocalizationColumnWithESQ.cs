using System;
using System.Globalization;
using Terrasoft.Common;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to write and read a localizable string column using the Entity model.
/// Use this approach when a column stores translated values per culture (e.g. Name on lookup entities).
/// LocalizableString holds one value per CultureInfo; Creatio persists each translation to a
/// separate resource row in the database and serves the correct value based on the current user culture.
/// </summary>
class HowToUpdateLocalizationColumnWithESQ {

    public void UpdateLocalizableColumn(UserConnection userConnection, Guid recordId) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("AccountType")
            .CreateEntity(userConnection);

        if (!entity.FetchFromDB(recordId)) {
            // Record not found — handle accordingly
            return;
        }

        // Build a LocalizableString with a translation for each culture you want to set
        var localizableString = new LocalizableString();
        localizableString.SetCultureValue(new CultureInfo("en-US"), "New Customer");
        localizableString.SetCultureValue(new CultureInfo("de-DE"), "Neuer Kunde");
        localizableString.SetCultureValue(new CultureInfo("uk-UA"), "Новий клієнт");

        // Assign the LocalizableString to the column — this replaces all existing culture values
        entity.SetColumnValue("Name", localizableString);
        entity.Save();

        // --- Reading back localized values ---

        // GetTypedColumnValue<string> returns the value for the current user's culture
        var nameForCurrentCulture = entity.GetTypedColumnValue<string>("Name");

        // GetTypedColumnValue<LocalizableString> returns the full object with all culture values
        var allTranslations = entity.GetTypedColumnValue<LocalizableString>("Name");
        var nameInGerman = allTranslations.GetCultureValue(new CultureInfo("de-DE"));
        var nameInUkrainian = allTranslations.GetCultureValue(new CultureInfo("uk-UA"));
    }
}
