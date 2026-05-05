using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to read and set record-level access rights using DBSecurityEngine.
/// Use this when Creatio's built-in role-based security is not granular enough and you need
/// to programmatically grant or revoke Read/Edit/Delete rights on individual records.
/// DBSecurityEngine is accessed via userConnection.DBSecurityEngine.
/// Rights are granted per (adminUnitId, schemaName, recordId, operation) combination —
/// adminUnitId is typically a role Id or user Id from SysAdminUnit.
/// </summary>
class HowToManageRecordAccessRights {

    // 1. Check what rights the current user has on a specific record
    public bool CanCurrentUserEditRecord(UserConnection userConnection,
        string schemaName, Guid recordId) {

        var dbSecurityEngine = userConnection.DBSecurityEngine;

        // Returns the combined right level flags for the current user on this record
        SchemaRecordRightLevels rightLevels =
            dbSecurityEngine.GetEntitySchemaRecordRightLevel(schemaName, recordId);

        // Compare against the level you need: CanRead, CanEdit, CanDelete
        return rightLevels >= SchemaRecordRightLevels.CanEdit;
    }

    // 2. Grant Read + Edit + Delete rights to a role on a record
    public void GrantFullAccess(UserConnection userConnection,
        Guid adminUnitId, string schemaName, Guid recordId) {

        var dbSecurityEngine = userConnection.DBSecurityEngine;
        var entitySchema = userConnection.EntitySchemaManager.GetInstanceByName(schemaName);

        // Set each operation separately — Allow means the right is explicitly granted
        dbSecurityEngine.SetEntitySchemaRecordOperationRightLevel(
            adminUnitId,
            schemaName,
            recordId,
            EntitySchemaRecordRightOperation.Read,
            EntitySchemaRecordRightLevel.Allow,
            entitySchema.UseDenyRecordRights,
            isInheritable: true);

        dbSecurityEngine.SetEntitySchemaRecordOperationRightLevel(
            adminUnitId,
            schemaName,
            recordId,
            EntitySchemaRecordRightOperation.Edit,
            EntitySchemaRecordRightLevel.Allow,
            entitySchema.UseDenyRecordRights,
            isInheritable: true);

        dbSecurityEngine.SetEntitySchemaRecordOperationRightLevel(
            adminUnitId,
            schemaName,
            recordId,
            EntitySchemaRecordRightOperation.Delete,
            EntitySchemaRecordRightLevel.Allow,
            entitySchema.UseDenyRecordRights,
            isInheritable: true);
    }

    // 3. Grant read-only access (no Edit, no Delete)
    public void GrantReadOnly(UserConnection userConnection,
        Guid adminUnitId, string schemaName, Guid recordId) {

        var dbSecurityEngine = userConnection.DBSecurityEngine;
        var entitySchema = userConnection.EntitySchemaManager.GetInstanceByName(schemaName);

        dbSecurityEngine.SetEntitySchemaRecordOperationRightLevel(
            adminUnitId,
            schemaName,
            recordId,
            EntitySchemaRecordRightOperation.Read,
            EntitySchemaRecordRightLevel.Allow,
            entitySchema.UseDenyRecordRights,
            isInheritable: true);
    }

    // 4. Remove all explicit rights for all roles on a record (reset to default)
    public void RevokeAllRights(UserConnection userConnection, string schemaName, Guid recordId) {
        var dbSecurityEngine = userConnection.DBSecurityEngine;

        dbSecurityEngine.ForceDeleteAllEntitySchemaRecordRightLevel(
            EntitySchemaRecordRightOperation.Read,   schemaName, recordId);
        dbSecurityEngine.ForceDeleteAllEntitySchemaRecordRightLevel(
            EntitySchemaRecordRightOperation.Edit,   schemaName, recordId);
        dbSecurityEngine.ForceDeleteAllEntitySchemaRecordRightLevel(
            EntitySchemaRecordRightOperation.Delete, schemaName, recordId);
    }
}
