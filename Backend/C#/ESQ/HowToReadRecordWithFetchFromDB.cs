using System;
using System.Collections.Generic;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to read a single record from the database using FetchFromDB.
/// FetchFromDB loads all column values into the entity instance and returns true if the record was found.
/// Use this when you need to read one specific record and work with its field values.
/// For reading multiple records or building complex filters, use EntitySchemaQuery (ESQ) instead.
/// </summary>
class HowToReadRecordWithFetchFromDB {

    // 1. Fetch by ID — direct primary key lookup, most common variant
    public void FetchById(UserConnection userConnection, Guid contactId) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("Contact")
            .CreateEntity(userConnection);

        bool found = entity.FetchFromDB(contactId);
        if (!found) {
            // Record does not exist — handle accordingly
            return;
        }

        // Read field values after a successful fetch
        var name      = entity.GetTypedColumnValue<string>("Name");
        var createdOn = entity.GetTypedColumnValue<DateTime>("CreatedOn");
        var countryId = entity.GetTypedColumnValue<Guid>("CountryId");
    }

    // 2. Fetch by a single column value
    public void FetchByColumn(UserConnection userConnection) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("Contact")
            .CreateEntity(userConnection);

        bool found = entity.FetchFromDB("Email", "john.doe@example.com");
        if (!found) {
            return;
        }

        var name = entity.GetTypedColumnValue<string>("Name");
    }

    // 3. Fetch by multiple column values using a Dictionary — all conditions are combined with AND
    public void FetchByDictionary(UserConnection userConnection, Guid countryId) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("Contact")
            .CreateEntity(userConnection);

        var filters = new Dictionary<string, object> {
            { "Email",     "john.doe@example.com" },
            { "CountryId", countryId }
        };

        bool found = entity.FetchFromDB(filters);
        if (!found) {
            return;
        }

        var name = entity.GetTypedColumnValue<string>("Name");
    }

    // 4. Fetch by ColumnValues
    public void FetchByColumnValues(UserConnection userConnection) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("Contact")
            .CreateEntity(userConnection);

        var values = new ColumnValues();
        values.Add("Email", "john.doe@example.com");

        bool found = entity.FetchFromDB(values);
        if (!found) {
            return;
        }

        var name = entity.GetTypedColumnValue<string>("Name");
    }
}
