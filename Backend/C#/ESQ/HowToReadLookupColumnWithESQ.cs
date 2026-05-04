using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to read columns from related entities using dot-path notation in ESQ.
/// Use "LookupColumn.ColumnName" to traverse a lookup — ESQ generates the JOIN automatically,
/// no manual join code required.
/// Always assign an explicit Name to lookup-path columns to avoid conflicts when the root entity
/// and the related entity share a column name (e.g. both have "Name").
/// Paths can be chained to traverse multiple lookups in one query: "Account.Owner.Name".
/// </summary>
class HowToReadLookupColumnWithESQ {

    public void ReadRelatedColumns(UserConnection userConnection) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Contact");

        esq.AddColumn("Name");
        esq.AddColumn("Email");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        // Dot-path: ESQ generates LEFT JOIN to Account and selects Account.Name
        // Explicit Name avoids collision with the Contact's own "Name" column
        var accountNameCol = esq.AddColumn("Account.Name");
        accountNameCol.Name = "AccountName";

        var accountPhoneCol = esq.AddColumn("Account.Phone");
        accountPhoneCol.Name = "AccountPhone";

        // Multi-level path — traverses two lookups: Contact → Account → Owner (Contact)
        var ownerNameCol = esq.AddColumn("Account.Owner.Name");
        ownerNameCol.Name = "AccountOwnerName";

        EntityCollection entities = esq.GetEntityCollection(userConnection);

        foreach (var entity in entities) {
            var contactName  = entity.GetTypedColumnValue<string>("Name");
            var accountName  = entity.GetTypedColumnValue<string>("AccountName");
            var accountPhone = entity.GetTypedColumnValue<string>("AccountPhone");
            var ownerName    = entity.GetTypedColumnValue<string>("AccountOwnerName");

            // custom logic
        }
    }
}
